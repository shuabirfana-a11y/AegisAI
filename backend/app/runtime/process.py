"""Bounded process-tree execution, including Gateway grandchildren.

Windows Job handles are parent-owned and non-inheritable. Workers wait for stdin
until attached, closing the child-launch race. POSIX workers share a new group.
This is termination control for fixed workers, not a hostile-code sandbox.
"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime

from app.runtime.contracts import (TaskInput, TaskArtifact, ToolReceipt, WorkerContext,
                                   ExecutionOutcome, WIRE_LIMIT, json_bytes)
from app.runtime.executor import failure, validate_outcome, validate_receipts
from app.tooling.contracts import ToolEnvelope
from app.utils.time import utcnow


class _BasicLimits(ctypes.Structure):
    _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                ('flags', wintypes.DWORD), ('min_ws', ctypes.c_size_t),
                ('max_ws', ctypes.c_size_t), ('active_limit', wintypes.DWORD),
                ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD),
                ('scheduling', wintypes.DWORD)]


class _IOCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        'read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [('basic', _BasicLimits), ('io', _IOCounters),
                ('process_mem', ctypes.c_size_t), ('job_mem', ctypes.c_size_t),
                ('peak_process_mem', ctypes.c_size_t), ('peak_job_mem', ctypes.c_size_t)]


class _Accounting(ctypes.Structure):
    _fields_ = [(name, ctypes.c_longlong) for name in ('user','kernel','period_user','period_kernel')] + [
        (name, wintypes.DWORD) for name in ('faults','total','active','terminated')]


class _ProcessIds(ctypes.Structure):
    # Fixed trusted workers need few descendants. Refuse unbounded enumeration.
    _fields_ = [('assigned',wintypes.DWORD),('count',wintypes.DWORD),
                ('ids',ctypes.c_size_t*256)]


def _kernel():
    dll = ctypes.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'CreateJobObjectW': ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
        'SetInformationJobObject': ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
        'AssignProcessToJobObject': ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
        'TerminateJobObject': ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        'QueryInformationJobObject': ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
        'CloseHandle': ([wintypes.HANDLE], wintypes.BOOL),
        'OpenProcess': ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
        'IsProcessInJob': ([wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)], wintypes.BOOL),
        'WaitForSingleObject': ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
    }
    for name, (args, returns) in signatures.items():
        fn = getattr(dll, name);fn.argtypes = args;fn.restype = returns
    return dll


class _WindowsJob:
    def __init__(self):
        self._process_handles = []
        self.dll = _kernel()
        self.handle = self.dll.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError('Unable to create task Job')
        limits = _ExtendedLimits();limits.basic.flags = 0x2000
        if not self.dll.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close();raise OSError('Unable to configure task Job')

    def attach(self, process):
        if not self.dll.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process._handle))):
            raise OSError('Unable to isolate task process')

    def terminate(self):
        capture_error = None
        try:
            ids = _ProcessIds()
            if not self.dll.QueryInformationJobObject(self.handle,3,ctypes.byref(ids),ctypes.sizeof(ids),None):
                raise OSError('Unable to enumerate owned task processes')
            if ids.count!=ids.assigned or ids.count>256:
                raise OSError('Task process enumeration exceeded limit')
            for pid in ids.ids[:ids.count]:
                # Retain process objects before asynchronous termination, so
                # PID reuse cannot turn an exit check into an unrelated wait.
                handle=self.dll.OpenProcess(0x101000,False,pid)
                if not handle:
                    if ctypes.get_last_error()==87:continue  # Already exited.
                    raise OSError('Unable to retain owned task process')
                member=wintypes.BOOL()
                if not self.dll.IsProcessInJob(handle,self.handle,ctypes.byref(member)):
                    self.dll.CloseHandle(handle)
                    raise OSError('Unable to verify task process ownership')
                if not member.value:
                    self.dll.CloseHandle(handle);continue
                self._process_handles.append(handle)
        except Exception as exc:
            capture_error=exc
        # Even a failed enumeration must still terminate the owned Job; it
        # becomes explicit cleanup failure, never uncontrolled continued work.
        if not self.dll.TerminateJobObject(self.handle, 1):
            raise OSError('Unable to terminate task Job')
        if capture_error is not None:raise OSError('Unable to confirm task process exits') from capture_error

    def empty(self):
        value = _Accounting()
        if not self.dll.QueryInformationJobObject(self.handle, 1, ctypes.byref(value), ctypes.sizeof(value), None):
            raise OSError('Unable to verify task Job')
        if value.active!=0:return False
        for handle in self._process_handles:
            status=self.dll.WaitForSingleObject(handle,0)
            if status==258:return False
            if status!=0:raise OSError('Unable to confirm task process exit')
        return True

    def close(self):
        for handle in self._process_handles:self.dll.CloseHandle(handle)
        self._process_handles.clear()
        if self.handle:
            self.dll.CloseHandle(self.handle);self.handle = None


class _PosixGroup:
    def __init__(self):
        self.pid = None

    def attach(self, process):
        self.pid = process.pid

    def terminate(self):
        if self.pid:
            try:os.killpg(self.pid, signal.SIGKILL)
            except ProcessLookupError:pass

    def empty(self):
        if self.pid is None:return True
        try:os.killpg(self.pid, 0)
        except ProcessLookupError:return True
        return False

    def close(self):
        pass


def create_isolation():
    return _WindowsJob() if os.name == 'nt' else _PosixGroup()


def process_alive(pid: int) -> bool:
    if os.name == 'nt':
        dll = _kernel();handle = dll.OpenProcess(0x100000, False, pid)
        if not handle:return False
        try:return dll.WaitForSingleObject(handle, 0) == 258
        finally:dll.CloseHandle(handle)
    try:os.kill(pid, 0)
    except ProcessLookupError:return False
    return True


class ProcessSupervisor:
    def __init__(self):
        self._cancelled = threading.Event()

    def cancel_all(self):
        """Abort this run's owned work when its coordinator cannot continue."""
        self._cancelled.set()

    def _command(self):
        return [sys.executable, '-m', 'app.runtime.worker']

    def execute(self, task, context: WorkerContext, dependencies, *, database_url=None):
        started = utcnow()
        cutoff = min(context.deadline, time.monotonic()+task.timeout_seconds)
        context = context.model_copy(update={'deadline': cutoff})
        if time.monotonic() >= cutoff:
            return ExecutionOutcome(artifact=failure(task, context, 'TASK_TIMEOUT', started=started))
        try:
            isolated = create_isolation()
        except Exception:
            return ExecutionOutcome(artifact=failure(task, context, 'TASK_ISOLATION_UNAVAILABLE', started=started))
        process = None;threads = [];chunks = [];overflow = threading.Event()
        guard = threading.Lock();total = 0;code = None;clean = True
        def drain(pipe, retain):
            nonlocal total
            try:
                while block := pipe.read1(65536):
                    with guard:
                        total += len(block)
                        if total > WIRE_LIMIT:overflow.set()
                        elif retain:chunks.append(block)
            except (OSError, ValueError):pass
        try:
            payload = json_bytes({'task': task.model_dump(mode='json'),
                                  'context': context.model_dump(mode='json'),
                                  'dependencies': {key: value.model_dump(mode='json')
                                                   for key, value in dependencies.items()}}, WIRE_LIMIT)
            env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[2]),
                   'PYTHONIOENCODING': 'utf-8'}
            if database_url:env['AEGIS_DATABASE_URL'] = database_url
            process = subprocess.Popen(self._command(), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, shell=False,
                start_new_session=os.name != 'nt',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            isolated.attach(process)
            def feed():
                try:process.stdin.write(payload);process.stdin.flush()
                except (OSError, ValueError):pass
                finally:
                    try:process.stdin.close()
                    except OSError:pass
            for target, args in ((drain, (process.stdout, True)), (drain, (process.stderr, False)), (feed, ())):
                thread = threading.Thread(target=target, args=args, daemon=True)
                thread.start();threads.append(thread)
            while process.poll() is None:
                if self._cancelled.is_set():code = 'RUN_CANCELLED';break
                if overflow.is_set():code = 'WORKER_OUTPUT_LIMIT';break
                if time.monotonic() >= cutoff:code = 'TASK_TIMEOUT';break
                time.sleep(.01)
            # A normal exit may have happened while the observer was asleep.
            # Observation after the deadline cannot unlock a successful branch.
            if code is None:
                if self._cancelled.is_set():code='RUN_CANCELLED'
                elif time.monotonic()>=cutoff:code='TASK_TIMEOUT'
            if code is None and process.returncode:code = 'WORKER_FAILED'
        except Exception:
            code = 'TASK_ISOLATION_UNAVAILABLE'
        finally:
            try:
                isolated.terminate()
                cleanup_deadline = time.monotonic()+2
                if process is not None:
                    if process.poll() is None:process.kill()
                    process.wait(timeout=max(.01,cleanup_deadline-time.monotonic()))
                while not isolated.empty() and time.monotonic() < cleanup_deadline:time.sleep(.01)
                clean = isolated.empty()
            except Exception:clean = False
            finally:isolated.close()
            for thread in threads:thread.join(timeout=.2)
            if process:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    try:pipe.close()
                    except (OSError, ValueError):pass
        if not clean:code = 'TASK_CLEANUP_FAILED'
        if overflow.is_set() and code not in ('TASK_CLEANUP_FAILED', 'TASK_TIMEOUT'):code = 'WORKER_OUTPUT_LIMIT'
        receipts = [];pending = {};artifact = None
        try:
            steps = TaskInput.model_validate(task.input_data).steps
            for line in b''.join(chunks).splitlines():
                try:event = json.loads(line)
                except (ValueError, UnicodeError):
                    if code:continue
                    raise ValueError('Invalid worker record')
                if event.get('kind') == 'tool_started':
                    index = event['call_index']
                    if index != len(receipts)+1 or index in pending or index > len(steps):
                        raise ValueError('Unexpected tool invocation')
                    step = steps[index-1]
                    if event['name'] != step.name or event['arguments'] != step.arguments:
                        raise ValueError('Tool invocation changed')
                    pending[index] = event
                elif event.get('kind') == 'tool_finished':
                    receipt = ToolReceipt.model_validate(event['receipt'])
                    if receipt.call_index not in pending:raise ValueError('Unstarted tool result')
                    pending.pop(receipt.call_index);receipts.append(receipt)
                elif event.get('kind') == 'artifact':
                    if artifact is not None:raise ValueError('Duplicate worker artifact')
                    artifact = TaskArtifact.model_validate(event['artifact'])
                else:raise ValueError('Unknown worker record')
            if code:
                for index, event in pending.items():
                    begin = datetime.fromisoformat(event['started_at']);now = utcnow()
                    receipts.append(ToolReceipt(call_index=index, name=event['name'], arguments=event['arguments'],
                        started_at=begin, finished_at=now,
                        envelope=ToolEnvelope(tool=event['name'], trace_id=str(context.trace_id),
                            duration_ms=max(0, int((now-begin).total_seconds()*1000)), status='failed',
                            errors=[{'code': code, 'message': 'Task worker was interrupted; side effects may be unknown'}])))
                artifact = failure(task, context, code, started=started, receipts=receipts)
            elif artifact is None or pending:
                raise ValueError('Incomplete worker protocol')
            return validate_outcome(task, context, ExecutionOutcome(artifact=artifact, receipts=receipts, cleanup_verified=clean))
        except Exception:
            # Keep complete, authorized receipts even if the final Artifact is
            # malformed. The fixed worker may have already performed a write.
            try:validate_receipts(task,context,receipts)
            except Exception:receipts=[]
            return ExecutionOutcome(artifact=failure(task, context, code or 'WORKER_PROTOCOL_ERROR',
                                    started=started,receipts=receipts),receipts=receipts,cleanup_verified=clean)
