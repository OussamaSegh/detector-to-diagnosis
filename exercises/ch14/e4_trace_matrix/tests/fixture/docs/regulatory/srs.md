# Fixture SRS

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-AAA-001 | The widget shall count every input. | widget | T |
| SRS-AAA-002 | The widget shall reject a negative input. | widget | T |
| SRS-AAA-003 | The widget shall process 1,000 inputs/s. | widget | M |
| SRS-BBB-001 | Withdrawn: replaced by SRS-AAA-002. | widget | T |
| SRS-BBB-002 | The gadget shall log every input. | gadget | T, I |

## Verification other than test

| ID | Method | Evidence |
|---|---|---|
| SRS-AAA-003 | M | measurements/widget.txt: 2,500 inputs/s |
| SRS-BBB-002 | I | Code review of the logger |
