# CVE Record Format

![GitHub Tag](https://img.shields.io/github/v/tag/cveproject/cve-schema)
![GitHub License](https://img.shields.io/github/license/cveproject/cve-schema)

The **CVE Record Format** is the [JSON schema][json_schema] defining the
structure of CVE records. It was previously called the "CVE Schema." This
repository is maintained by the [CVE Quality Working Group][qwg] (QWG) under
the [QWG Charter][qwg_charter].

This repository is part of the [CVE Project][cve] and is governed by CVE's
[Professional Code of Conduct][coc].

---

## Read the Record Format

The version of the schema found on the [`main` branch][branch_main] of this
repository is the current production version used by CVE Services. The
development version, which reflects work-in-progress changes planned for future
production versions, is found on the [`develop` branch][branch_develop].

### Production Version

The current production version of the CVE Record Format is available in several
forms:

- [Separate files][fmt_1]
- [Single file][fmt_2]
- [Interactive][fmt_3]
- [Mindmap][fmt_4]

Additionally, the CVE Record Format incorporates mechanisms for encoding
product identity and version information, which are [documented in greater
detail][products_and_versions].

### Development Version

The development version of the CVE Record Format can be found in the
[`develop` branch][branch_develop]:

- [Separate files][fmt_5]

## Examples

- [Example with minimum required fields][ex_1]
- [More complete example][ex_2]
- [A basic example of a `cnaContainer`, to be used with CVE Services][ex_3]
- [An advanced example of a `cnaContainer`, to be used with CVE Services][ex_4]

## Known Issues

The CVE Services page on the CVE site tracks
[known issues with the CVE Record Format][known_issues].

## Contributing

Work in this repository is managed by the CVE [Quality Working Group][qwg]. QWG
meetings are open to CVE authorized program members, including:

- Members of the [CVE Board][cve_board]
- Representatives of [CVE Numbering Authorities (CNAs)][cve_cnas]
- Representatives of [Authorized Data Publishers (ADPs)][cve_adps]
- Participants from the [CVE Secretariat][cve_secretariat] (currently
  [The MITRE Corporation][mitre])

On a case-by-case basis, the QWG can invite to participate, through consensus,
individuals who are not CVE program members. To request admission to the QWG,
please contact one of the QWG Co-Chairs, currently
[Chris Coffin (MITRE)][cochair_chris_coffin],
[MegaZone (F5)][cochair_megazone], or
[David Waltermire (GSA FedRAMP)][cochair_dave_waltermire].

Any individual is welcome to participate via [Issues][gh_issues],
[Discussions][gh_discussions], and [Pull Requests][gh_prs], including opening
issues, creating proposals, commenting on existing proposals in Pull
Requests, and asking questions about the Record Format. Decisions on how to
proceed with any proposal are made by the Quality Working Group via consensus.
Final authority for approving or rejecting changes to the CVE Record Format
lies with the [CVE Board][cve_board].

All participation in this project is subject to the rules and procedures of the
[CVE Professional Code of Conduct][coc].

[branch_develop]: https://github.com/CVEProject/cve-schema/tree/develop
[branch_main]: https://github.com/CVEProject/cve-schema/tree/main
[cve]: https://www.cve.org/
[cve_board]: https://www.cve.org/ProgramOrganization/Board
[cve_cnas]: https://www.cve.org/ProgramOrganization/CNAs
[cve_adps]: https://www.cve.org/ProgramOrganization/ADPs
[cve_secretariat]: https://www.cve.org/ResourcesSupport/Glossary?activeTerm=glossarySecretariat
[coc]: https://www.cve.org/ResourcesSupport/AllResources/ProfessionalCodeOfConduct
[cochair_chris_coffin]: https://www.linkedin.com/in/christopher-coffin-1573437/
[cochair_dave_waltermire]: https://www.linkedin.com/in/david-waltermire-024b1710a/
[cochair_megazone]: https://www.linkedin.com/in/megazone/
[ex_1]: https://github.com/cveproject/cve-schema/blob/main/schema/docs/full-record-basic-example.json
[ex_2]: https://github.com/cveproject/cve-schema/blob/main/schema/docs/full-record-advanced-example.json
[ex_3]: https://github.com/cveproject/cve-schema/blob/main/schema/docs/cnaContainer-basic-example.json
[ex_4]: https://github.com/cveproject/cve-schema/blob/main/schema/docs/cnaContainer-advanced-example.json
[fmt_1]: https://github.com/CVEProject/cve-schema/blob/main/schema/CVE_Record_Format.json
[fmt_2]: https://github.com/CVEProject/cve-schema/blob/main/schema/docs/CVE_Record_Format_bundled.json
[fmt_3]: https://cveproject.github.io/cve-schema/schema/docs/
[fmt_4]: https://cveproject.github.io/cve-schema/schema/docs/mindmap.html
[fmt_5]: https://github.com/CVEProject/cve-schema/blob/develop/schema/CVE_Record_Format.json
[gh_issues]: https://github.com/CVEProject/cve-schema/issues
[gh_discussions]: https://github.com/CVEProject/cve-schema/discussions
[gh_prs]: https://github.com/CVEProject/cve-schema/pulls
[json_schema]: https://json-schema.org/
[known_issues]: https://www.cve.org/AllResources/CveServices
[mitre]: https://www.mitre.org/
[products_and_versions]: https://github.com/CVEProject/cve-schema/blob/main/schema/docs/versions.md
[qwg]: https://github.com/CVEProject/quality-workgroup
[qwg_charter]: https://github.com/CVEProject/quality-workgroup/blob/main/README.md
