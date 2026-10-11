# 迁移与可复现检查

固定工具：SQLAlchemy 2.0.54、Alembic 1.20.0、psycopg 3.3.6、pytest 9.1.1；锁定文件见backend/requirements.txt。0001_initial读取同目录0001_schema.json的固定DDL，不导入当前ORM、不在启动时create_all。初始版本包含五schema、43表、约束/索引和22个历史触发器。发布后不可编辑0001；新功能新revision，autogenerate必须人工审阅，数据迁移与schema迁移明确分开。

实际PostgreSQL17.11测试：首次upgrade→downgrade base→确认五schema不存在→重新upgrade→43表与ORM metadata零差异→22历史触发器存在。真库记录见migration_validation.json，测试逐项见database_tests.json；没有SQLite替代或静默skip。downgrade仅用于本项目空专用测试库，不是生产回滚默认路径；会删除全schema数据。生产采用expand/contract、备份/恢复或forward repair，不手工ALTER生产。

本机重现流程见[backend启动说明](../../backend/README.md)，Python虚拟环境及PostgreSQL便携runtime由本阶段准备，测试只允许aegis_phase5_test。启动脚本将cluster限定本工作区work，监听127.0.0.1，不注册Windows服务；测试结束stop。trust仅临时本机测试，生产必须SCRAM并分角色，连接secret从Environment/Secret Manager供给，URL参数不写日志。

后续迁移必须覆盖空库升级、已有schema升级、升级重复幂等、数据兼容、需要回退时的往返、ORM drift、索引/触发器/许可访问。长DDL索引/column回填要基于真实数据量测锁影响，不声称本轮小库已满足并发SLA。新enum用命名CHECK/lookup升级，避免无必要全局PostgreSQL ENUM变更；pgvector是独立后续迁移。

本轮实际发现并修正复合UNIQUE命名碰撞，命名规范采用全部列名，防两个id前缀复合约束同名。Windows便携pg_ctl的后台继承pipe问题已改为日志文件，避免等待服务器生命周期。红测试确认幂等/复核未实现时失败，后续完整套件通过；修复过程不是产品Benchmark。

生产备份/restore演练尚未执行，跨进程并发压力、完整auth/最小数据库角色仍未实现。应用需要validated actor与权限、受控Raw读取、安全URL获取和结果scope检查，这些属于下一阶段，不由模型自动提供。
