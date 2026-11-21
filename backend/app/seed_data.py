"""Starter methodology library (the 13 examples named in the product brief).

Format: stages are (name, description, [(activity, expected output), ...]);
deliverables are (name, classification, stage index or None)."""

M, R, O = "mandatory", "recommended", "optional"

METHODOLOGIES: list[dict] = [
    {
        "name": "Starting a new software project",
        "purpose": "Take an idea to an agreed, planned and runnable project foundation.",
        "when_to_use": "At the start of any new product, service or internal tool.",
        "prerequisites": "An initial idea or problem statement; someone who can make decisions.",
        "tools": "This workspace, a Git repository, a diagramming tool.",
        "common_risks": "Building before the problem is understood; unclear scope; no definition of done.",
        "completion_criteria": "Brief agreed, architecture chosen, repository and environments running, first milestone planned.",
        "stages": [
            (
                "Discovery",
                "Understand the problem and who has it.",
                [
                    ("Write the problem statement and target users", "Problem statement agreed"),
                    ("Identify stakeholders and constraints", "Stakeholder and constraints list"),
                    ("Separate confirmed requirements from assumptions", "Assumptions log"),
                ],
            ),
            (
                "Requirements",
                "Define what must be true when the project succeeds.",
                [
                    (
                        "Capture functional and non-functional requirements",
                        "Requirements list with priorities",
                    ),
                    ("Define scope and out-of-scope", "Scope statement"),
                    ("Agree acceptance criteria for the MVP", "MVP acceptance criteria"),
                ],
            ),
            (
                "Architecture",
                "Choose a sensible, documented technical approach.",
                [
                    ("Assess technology options", "Technology stack assessment"),
                    ("Draw the high-level architecture", "High-level architecture diagram"),
                    ("Record key decisions as ADRs", "Architecture decision records"),
                ],
            ),
            (
                "Foundation",
                "Make the project runnable for everyone.",
                [
                    ("Create the repository, structure and README", "Repository with setup guide"),
                    (
                        "Set up environments, configuration and secrets handling",
                        "Working local environment",
                    ),
                    ("Add automated tests and linting", "Passing CI or local test run"),
                ],
            ),
            (
                "Delivery plan",
                "Turn the scope into milestones and tasks.",
                [
                    ("Break the MVP into milestones and tasks", "Delivery roadmap"),
                    ("Identify risks and dependencies", "Risk register"),
                ],
            ),
        ],
        "deliverables": [
            ("Project brief", M, 0),
            ("Technical requirements", M, 1),
            ("High-level architecture diagram", R, 2),
            ("Architecture decision records", R, 2),
            ("Development setup guide", M, 3),
            ("Delivery roadmap", M, 4),
            ("Risk register", R, 4),
        ],
    },
    {
        "name": "Assessing an existing codebase",
        "purpose": "Understand an existing system well enough to change, rescue or replace it safely.",
        "when_to_use": "When inheriting, auditing or planning major work on a codebase you did not build.",
        "prerequisites": "Read access to the repository and documentation; a contact who knows the system.",
        "tools": "Git history, dependency scanners, test runners, profilers, diagramming tool.",
        "common_risks": "Judging code without domain context; missing undocumented behaviour; changing before measuring.",
        "completion_criteria": "Current state documented, risks and gaps ranked, options compared and a roadmap agreed.",
        "stages": [
            (
                "Discovery and domain research",
                "Understand why the system exists and who relies on it.",
                [
                    ("Project discovery: goals, users, stakeholders", "Discovery notes"),
                    ("Domain research", "Domain glossary and key business rules"),
                ],
            ),
            (
                "Repository and documentation review",
                "Find out what exists.",
                [
                    ("Repository inspection: structure, history, activity", "Repository overview"),
                    ("Existing documentation review", "Documentation gap list"),
                    ("Dependency analysis", "Dependency inventory with versions and risks"),
                ],
            ),
            (
                "Current-state architecture",
                "Describe the system as it is, not as intended.",
                [
                    (
                        "Map components, data flows and integrations",
                        "Current-state architecture diagram",
                    ),
                    ("Backend review", "Backend findings"),
                    ("Frontend review", "Frontend findings"),
                    ("Database review", "Data model and quality findings"),
                    ("API review", "API inventory and issues"),
                ],
            ),
            (
                "Quality, security and operations",
                "Measure risk.",
                [
                    ("Code quality review", "Code quality findings"),
                    ("Security and privacy review", "Security findings ranked by severity"),
                    ("Testing review", "Test coverage and gaps"),
                    ("Performance and reliability review", "Performance and reliability findings"),
                    ("Technical debt register", "Ranked technical debt list"),
                ],
            ),
            (
                "Analysis and options",
                "Decide what to do.",
                [
                    ("Gap analysis against goals", "Gap analysis"),
                    ("Risk assessment", "Risk register"),
                    ("Options analysis (fix, refactor, replace)", "Options comparison"),
                    ("Proposed architecture", "Proposed architecture diagram"),
                ],
            ),
            (
                "Roadmap",
                "Plan the change.",
                [
                    ("Implementation roadmap", "Phased roadmap with milestones"),
                    ("Stakeholder presentation", "Presentation of findings and recommendation"),
                ],
            ),
        ],
        "deliverables": [
            ("Codebase assessment", M, None),
            ("Current-state architecture", M, 2),
            ("Risk register", M, 4),
            ("Proposed architecture", R, 4),
            ("Implementation roadmap", M, 5),
            ("Stakeholder presentation", O, 5),
        ],
    },
    {
        "name": "Conducting domain and technical research",
        "purpose": "Answer a specific question with evidence and record it for reuse.",
        "when_to_use": "Before a significant decision, or when entering an unfamiliar domain or technology.",
        "prerequisites": "A clearly worded research question.",
        "tools": "Official documentation, papers, prototypes, the Knowledge & Research library.",
        "common_risks": "Unclear question; relying on unverified sources; not recording limitations.",
        "completion_criteria": "Findings, options and recommendation recorded with sources and verification status.",
        "stages": [
            (
                "Frame",
                "Make the question answerable.",
                [
                    ("Write the research question and objective", "Research question"),
                    ("Define evaluation criteria", "Criteria list"),
                ],
            ),
            (
                "Investigate",
                "Gather evidence.",
                [
                    ("Collect sources (prefer official documentation)", "Source list"),
                    (
                        "Investigate options; prototype where cheap",
                        "Option notes and prototype results",
                    ),
                ],
            ),
            (
                "Synthesise",
                "Turn evidence into a recommendation.",
                [
                    ("Compare options against criteria", "Comparison table"),
                    ("Write conclusions, recommendations and limitations", "Research record"),
                ],
            ),
        ],
        "deliverables": [("Research report", M, 2)],
    },
    {
        "name": "Performing an architecture assessment",
        "purpose": "Evaluate whether an architecture meets its quality goals and where it is at risk.",
        "when_to_use": "Before scaling, after incidents, or when choosing between architectural options.",
        "prerequisites": "Known quality goals (performance, availability, security, cost).",
        "tools": "Diagrams, metrics, load tests, threat modelling.",
        "common_risks": "Assessing without agreed quality goals; ignoring operations and cost.",
        "completion_criteria": "Quality attributes scored with evidence and prioritised recommendations.",
        "stages": [
            (
                "Context",
                "Agree what good looks like.",
                [("Agree quality attributes and scenarios", "Quality attribute scenarios")],
            ),
            (
                "Analyse",
                "Evaluate the architecture against each scenario.",
                [
                    ("Map the architecture and deployment", "Architecture and deployment diagrams"),
                    (
                        "Evaluate each scenario; identify risks and trade-offs",
                        "Risks and trade-offs",
                    ),
                ],
            ),
            (
                "Recommend",
                "Prioritise improvements.",
                [("Write prioritised recommendations", "Architecture assessment report")],
            ),
        ],
        "deliverables": [
            ("Architecture assessment report", M, 2),
            ("Deployment architecture", R, 1),
        ],
    },
    {
        "name": "Designing a future-state architecture",
        "purpose": "Define a target architecture and a safe path to reach it.",
        "when_to_use": "When the current system cannot meet future goals.",
        "prerequisites": "Current-state architecture and business goals.",
        "tools": "Diagramming tool, ADRs, cost estimates.",
        "common_risks": "Big-bang rewrites; target state disconnected from constraints.",
        "completion_criteria": "Target architecture, transition states and roadmap agreed.",
        "stages": [
            (
                "Goals and constraints",
                "",
                [("Document goals, constraints and principles", "Architecture principles")],
            ),
            (
                "Target design",
                "",
                [
                    (
                        "Design target components and data architecture",
                        "Detailed architecture diagram",
                    ),
                    ("Design security architecture", "Security architecture"),
                    ("Record decisions", "Architecture decision records"),
                ],
            ),
            ("Transition", "", [("Define transition states and roadmap", "Migration roadmap")]),
        ],
        "deliverables": [
            ("Proposed architecture", M, 1),
            ("Data architecture", R, 1),
            ("Security architecture", R, 1),
            ("Delivery roadmap", M, 2),
        ],
    },
    {
        "name": "Creating a design system",
        "purpose": "Establish consistent, accessible, reusable UI foundations.",
        "when_to_use": "For any product with more than a handful of screens, or when merging design languages.",
        "prerequisites": "Brand guidance (if any); inventory of existing screens.",
        "tools": "Design tool, component library (e.g. shadcn/ui), accessibility checker.",
        "common_risks": "Designing components nobody uses; skipping accessibility; no documentation.",
        "completion_criteria": "Documented tokens and core components used by the product, meeting WCAG AA.",
        "stages": [
            (
                "Audit",
                "",
                [("Inventory colours, type, spacing and components in use", "UI inventory")],
            ),
            (
                "Foundations",
                "",
                [
                    ("Define colour, typography, spacing and layout tokens", "Design tokens"),
                    ("Check contrast and focus states", "Accessibility check results"),
                ],
            ),
            (
                "Components",
                "",
                [
                    (
                        "Build buttons, inputs, selectors, cards, tables, badges, dialogues, navigation",
                        "Component library",
                    ),
                    ("Define empty, loading and error states", "State patterns"),
                ],
            ),
            ("Document", "", [("Write usage guidance", "Design system specification")]),
        ],
        "deliverables": [("Design system specification", M, 3)],
    },
    {
        "name": "Building a clickable prototype",
        "purpose": "Test an idea with users before building it properly.",
        "when_to_use": "When the solution is uncertain or stakeholder buy-in is needed.",
        "prerequisites": "Problem statement and target users.",
        "tools": "Prototyping tool or a throwaway front end.",
        "common_risks": "Prototype mistaken for production; testing with the wrong users.",
        "completion_criteria": "Prototype tested with users and findings recorded.",
        "stages": [
            ("Plan", "", [("Choose key journeys and questions to answer", "Prototype plan")]),
            ("Build", "", [("Build the clickable journeys", "Prototype")]),
            (
                "Test",
                "",
                [
                    ("Run sessions with users", "Session notes"),
                    ("Summarise findings and decide next steps", "Findings report"),
                ],
            ),
        ],
        "deliverables": [("Prototype", M, 1), ("Research report", R, 2)],
    },
    {
        "name": "Developing an AI application",
        "purpose": "Ship a reliable application that uses a language model for a defined task.",
        "when_to_use": "When an LLM capability (generation, extraction, classification) serves a clear user need.",
        "prerequisites": "A defined task, example inputs and a way to judge good output.",
        "tools": "Model provider SDK behind an interface, evaluation dataset, logging.",
        "common_risks": "No evaluation; prompt changes without regression checks; leaking sensitive data; presenting AI output as fact.",
        "completion_criteria": "Evaluated against a dataset, guarded, monitored and reviewable by users.",
        "stages": [
            (
                "Define",
                "",
                [
                    ("Define the task, users and failure modes", "Task specification"),
                    ("Collect representative examples", "Evaluation dataset"),
                ],
            ),
            (
                "Build",
                "",
                [
                    ("Implement behind a provider-independent interface", "Working integration"),
                    ("Add guardrails and human review", "Review workflow"),
                ],
            ),
            ("Evaluate", "", [("Measure quality against the dataset", "Evaluation results")]),
            ("Operate", "", [("Add monitoring, cost tracking and feedback", "Operations runbook")]),
        ],
        "deliverables": [("AI evaluation strategy", M, 2), ("Technical requirements", R, 0)],
    },
    {
        "name": "Developing an agentic AI system",
        "purpose": "Build an AI agent that uses tools to complete multi-step tasks safely.",
        "when_to_use": "When a task needs planning, tool use and iteration rather than one model call.",
        "prerequisites": "Clear task boundaries, tool definitions and permission rules.",
        "tools": "Agent framework, sandboxed tools, tracing, evaluation harness.",
        "common_risks": "Unbounded actions; missing approval for destructive steps; untraceable decisions.",
        "completion_criteria": "Agent completes evaluated tasks within permissions, with traces and human checkpoints.",
        "stages": [
            (
                "Design",
                "",
                [
                    ("Define goals, tools and permissions", "Agent design"),
                    ("Identify actions needing human approval", "Approval rules"),
                ],
            ),
            (
                "Build",
                "",
                [
                    ("Implement tools and the agent loop", "Working agent"),
                    ("Add tracing and logging", "Trace output"),
                ],
            ),
            ("Evaluate", "", [("Run task evaluations and red-team tests", "Evaluation report")]),
        ],
        "deliverables": [("AI evaluation strategy", M, 2), ("Security architecture", R, 0)],
    },
    {
        "name": "Conducting AI evaluation",
        "purpose": "Measure whether an AI feature is good enough, and keep it that way.",
        "when_to_use": "Before launching any AI feature and after every model or prompt change.",
        "prerequisites": "A defined task and examples of good and bad output.",
        "tools": "Evaluation dataset, scoring rubric, automated graders, spreadsheet.",
        "common_risks": "Unrepresentative datasets; grading by vibes; no baseline.",
        "completion_criteria": "Repeatable evaluation with a baseline and an agreed pass threshold.",
        "stages": [
            ("Criteria", "", [("Define success criteria and rubric", "Evaluation rubric")]),
            ("Dataset", "", [("Build a representative, labelled dataset", "Evaluation dataset")]),
            (
                "Run",
                "",
                [
                    ("Run evaluation and record a baseline", "Baseline results"),
                    ("Analyse failures", "Failure analysis"),
                ],
            ),
        ],
        "deliverables": [("AI evaluation strategy", M, 0)],
    },
    {
        "name": "Conducting software testing",
        "purpose": "Give justified confidence that the software works and keeps working.",
        "when_to_use": "Throughout every software project.",
        "prerequisites": "Requirements and acceptance criteria.",
        "tools": "Unit test framework, end-to-end tool (e.g. Playwright), CI.",
        "common_risks": "Testing only happy paths; tests coupled to implementation; skipping failure scenarios.",
        "completion_criteria": "Strategy agreed, critical journeys automated and failures documented.",
        "stages": [
            (
                "Strategy",
                "",
                [("Write the testing strategy and risk-based priorities", "Testing strategy")],
            ),
            (
                "Automate",
                "",
                [
                    ("Write unit and API tests for business rules", "Passing unit tests"),
                    ("Automate critical user journeys end to end", "Passing end-to-end tests"),
                ],
            ),
            (
                "Assure",
                "",
                [
                    ("Test failure scenarios and accessibility", "Test results"),
                    ("Record known defects and limitations", "Known issues list"),
                ],
            ),
        ],
        "deliverables": [("Testing strategy", M, 0), ("Testing documentation", R, 2)],
    },
    {
        "name": "Preparing a deployment",
        "purpose": "Release safely with a way back.",
        "when_to_use": "Before any production or staging release.",
        "prerequisites": "A tested build and access to the target environment.",
        "tools": "CI/CD, infrastructure as code, monitoring, backups.",
        "common_risks": "No rollback; untested migrations; secrets in configuration.",
        "completion_criteria": "Released, verified, monitored, with a tested rollback and release notes.",
        "stages": [
            (
                "Prepare",
                "",
                [
                    ("Check configuration, secrets and migrations", "Release checklist"),
                    ("Take a backup and verify restore", "Verified backup"),
                ],
            ),
            ("Release", "", [("Deploy and run smoke tests", "Smoke test results")]),
            ("Verify", "", [("Monitor and confirm success; communicate", "Release notes")]),
        ],
        "deliverables": [("Deployment architecture", R, 0), ("Release notes", M, 2)],
    },
    {
        "name": "Troubleshooting production issues",
        "purpose": "Restore service quickly, then fix and learn.",
        "when_to_use": "When users are affected by a fault in a live system.",
        "prerequisites": "Access to logs, metrics and the deployment pipeline.",
        "tools": "Logs, metrics, tracing, version history.",
        "common_risks": "Changing several things at once; no record of what was tried; skipping the review.",
        "completion_criteria": "Service restored, root cause fixed, troubleshooting guide recorded.",
        "stages": [
            (
                "Stabilise",
                "",
                [
                    ("Assess impact and communicate", "Incident notes"),
                    ("Mitigate (roll back, disable, scale)", "Service restored"),
                ],
            ),
            (
                "Diagnose",
                "",
                [
                    ("Gather symptoms, environment and timeline", "Timeline"),
                    ("Find the root cause, one change at a time", "Root cause"),
                ],
            ),
            (
                "Resolve and learn",
                "",
                [
                    ("Fix and verify", "Verified fix"),
                    ("Write a troubleshooting guide and lessons learned", "Troubleshooting guide"),
                ],
            ),
        ],
        "deliverables": [("Troubleshooting guide", M, 2)],
    },
]
