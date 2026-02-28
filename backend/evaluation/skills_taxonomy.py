"""Curated technology skills taxonomy for ATS skill-coverage scoring.

Organized by category. Each category is a frozenset of lowercase canonical skill names.
ALL_SKILLS is the union used by the PhraseMatcher in the scorer.

TECH_SYNONYMS maps abbreviations/variations to their canonical forms, enabling
the scorer to treat "K8s" and "Kubernetes" as the same skill.
"""

import re

# ── Programming Languages ─────────────────────────────────────────────
LANGUAGES = frozenset({
    "python", "java", "javascript", "typescript", "c", "c++", "c#",
    "go", "golang", "rust", "ruby", "php", "swift", "kotlin", "scala",
    "r", "matlab", "perl", "lua", "haskell", "erlang", "elixir",
    "objective-c", "dart", "groovy", "clojure", "f#", "julia",
    "assembly", "vhdl", "verilog", "cobol", "fortran", "lisp",
    "scheme", "ocaml", "zig", "nim", "crystal", "solidity",
    "bash", "shell", "powershell", "sql", "plsql", "t-sql",
    "html", "css", "sass", "scss", "less",
})

# ── Frontend Frameworks & Libraries ───────────────────────────────────
FRONTEND = frozenset({
    "react", "reactjs", "react.js", "angular", "angularjs", "vue",
    "vue.js", "vuejs", "svelte", "next.js", "nextjs", "nuxt",
    "nuxt.js", "gatsby", "remix", "astro", "solid.js", "solidjs",
    "jquery", "backbone.js", "ember.js", "preact", "lit",
    "alpine.js", "htmx", "stimulus", "turbo",
    "redux", "zustand", "mobx", "recoil", "jotai", "xstate",
    "react query", "tanstack query", "swr",
    "tailwind", "tailwindcss", "tailwind css", "bootstrap",
    "material ui", "mui", "chakra ui", "ant design", "shadcn",
    "styled-components", "emotion", "css modules",
    "webpack", "vite", "rollup", "esbuild", "parcel", "turbopack",
    "storybook", "figma", "sketch", "adobe xd",
    "three.js", "d3.js", "d3", "chart.js", "echarts",
})

# ── Backend Frameworks ────────────────────────────────────────────────
BACKEND = frozenset({
    "node.js", "nodejs", "node", "express", "express.js", "fastify",
    "nest.js", "nestjs", "koa", "hapi",
    "django", "flask", "fastapi", "tornado", "celery", "gunicorn",
    "uvicorn", "starlette", "aiohttp",
    "spring", "spring boot", "spring framework", "quarkus", "micronaut",
    "hibernate", "maven", "gradle",
    "ruby on rails", "rails", "sinatra",
    "asp.net", ".net", ".net core", "blazor", "entity framework",
    "laravel", "symfony", "codeigniter",
    "gin", "echo", "fiber", "chi",
    "phoenix", "actix", "axum", "rocket",
})

# ── Databases ─────────────────────────────────────────────────────────
DATABASES = frozenset({
    "postgresql", "postgres", "mysql", "mariadb", "sqlite",
    "oracle", "sql server", "mssql", "db2",
    "mongodb", "mongoose", "couchdb", "couchbase",
    "redis", "memcached", "valkey",
    "elasticsearch", "opensearch", "solr", "lucene",
    "cassandra", "dynamodb", "scylla", "hbase",
    "neo4j", "arangodb", "dgraph", "neptune",
    "influxdb", "timescaledb", "clickhouse", "druid",
    "snowflake", "bigquery", "redshift", "databricks",
    "cockroachdb", "tidb", "yugabytedb", "planetscale",
    "supabase", "firebase", "firestore",
    "prisma", "typeorm", "sequelize", "sqlalchemy", "knex",
})

# ── Cloud Platforms & Services ────────────────────────────────────────
CLOUD = frozenset({
    "aws", "amazon web services", "ec2", "s3", "lambda", "ecs",
    "eks", "fargate", "rds", "aurora", "dynamodb", "sqs", "sns",
    "kinesis", "cloudformation", "cdk", "cloudwatch", "iam",
    "route 53", "cloudfront", "api gateway", "step functions",
    "sagemaker", "bedrock", "glue", "athena", "emr",
    "azure", "microsoft azure", "azure devops", "azure functions",
    "azure kubernetes service", "aks", "azure blob storage",
    "azure sql", "azure cosmos db", "azure pipelines",
    "gcp", "google cloud", "google cloud platform",
    "compute engine", "cloud run", "cloud functions",
    "gke", "cloud storage", "cloud sql", "pub/sub", "dataflow",
    "vertex ai", "cloud build",
    "heroku", "vercel", "netlify", "render", "fly.io",
    "digitalocean", "linode", "vultr",
    "cloudflare", "cloudflare workers", "cloudflare pages",
})

# ── DevOps, CI/CD & Infrastructure ───────────────────────────────────
DEVOPS = frozenset({
    "docker", "dockerfile", "docker compose", "docker-compose",
    "kubernetes", "k8s", "helm", "kustomize", "istio", "linkerd",
    "openshift", "rancher",
    "terraform", "pulumi", "ansible", "chef", "puppet", "saltstack",
    "vagrant", "packer",
    "jenkins", "github actions", "gitlab ci", "circleci",
    "travis ci", "buildkite", "argo cd", "argocd", "flux",
    "spinnaker", "tekton", "drone",
    "prometheus", "grafana", "datadog", "new relic", "splunk",
    "elk stack", "logstash", "kibana", "jaeger", "zipkin",
    "pagerduty", "opsgenie",
    "nginx", "apache", "caddy", "envoy", "haproxy", "traefik",
    "consul", "vault", "etcd", "zookeeper",
    "git", "github", "gitlab", "bitbucket", "mercurial",
    "linux", "unix", "ubuntu", "centos", "rhel", "debian",
    "windows server", "macos",
    "ci/cd", "continuous integration", "continuous deployment",
    "continuous delivery", "infrastructure as code", "iac",
    "site reliability engineering", "sre",
    "observability", "monitoring", "logging", "alerting",
})

# ── Data Science & Machine Learning ──────────────────────────────────
DATA_SCIENCE = frozenset({
    "machine learning", "deep learning", "artificial intelligence", "ai",
    "neural network", "nlp", "natural language processing",
    "computer vision", "reinforcement learning",
    "tensorflow", "pytorch", "keras", "jax", "mxnet",
    "scikit-learn", "sklearn", "xgboost", "lightgbm", "catboost",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
    "jupyter", "jupyter notebook", "colab",
    "hugging face", "huggingface", "transformers", "bert", "gpt",
    "llm", "large language model", "langchain", "langgraph",
    "rag", "retrieval augmented generation",
    "prompt engineering", "fine-tuning", "rlhf",
    "opencv", "yolo", "detectron", "stable diffusion",
    "mlflow", "wandb", "weights and biases", "dvc",
    "feature engineering", "model deployment", "mlops",
    "a/b testing", "statistical analysis", "hypothesis testing",
    "regression", "classification", "clustering",
    "random forest", "gradient boosting", "svm", "knn",
    "cnn", "rnn", "lstm", "transformer", "attention mechanism",
    "generative ai", "gen ai",
})

# ── Data Engineering & Big Data ───────────────────────────────────────
DATA_ENGINEERING = frozenset({
    "apache spark", "spark", "pyspark",
    "apache kafka", "kafka", "kafka streams",
    "apache flink", "flink",
    "apache airflow", "airflow", "dagster", "prefect", "luigi",
    "apache beam", "dataflow",
    "hadoop", "hdfs", "mapreduce", "hive", "pig", "presto", "trino",
    "dbt", "data build tool",
    "etl", "elt", "data pipeline", "data warehouse", "data lake",
    "data lakehouse", "delta lake", "iceberg", "hudi",
    "data modeling", "dimensional modeling", "star schema",
    "data governance", "data quality", "data catalog",
    "fivetran", "airbyte", "stitch", "talend",
    "looker", "tableau", "power bi", "metabase", "superset",
    "snowflake", "bigquery", "redshift", "databricks",
})

# ── Security ──────────────────────────────────────────────────────────
SECURITY = frozenset({
    "cybersecurity", "information security", "infosec",
    "penetration testing", "pen testing", "ethical hacking",
    "vulnerability assessment", "threat modeling",
    "soc", "security operations center",
    "siem", "soar", "ids", "ips",
    "oauth", "oauth2", "openid connect", "oidc", "saml",
    "jwt", "json web token", "api key", "mfa", "2fa",
    "ssl", "tls", "https", "encryption", "pki",
    "owasp", "cve", "zero trust",
    "firewall", "waf", "vpn", "ipsec",
    "compliance", "gdpr", "hipaa", "soc 2", "pci dss", "iso 27001",
    "devsecops", "sast", "dast", "container security",
})

# ── Mobile Development ────────────────────────────────────────────────
MOBILE = frozenset({
    "ios", "android", "mobile development",
    "react native", "flutter", "xamarin", "ionic", "cordova",
    "swiftui", "uikit", "jetpack compose", "android studio",
    "xcode", "cocoapods", "carthage", "spm",
    "expo", "capacitor",
    "app store", "google play", "testflight",
    "push notifications", "deep linking",
    "mobile testing", "appium", "detox",
})

# ── Testing & QA ──────────────────────────────────────────────────────
TESTING = frozenset({
    "unit testing", "integration testing", "end-to-end testing", "e2e testing",
    "test-driven development", "tdd", "behavior-driven development", "bdd",
    "jest", "mocha", "chai", "jasmine", "vitest", "cypress",
    "playwright", "selenium", "puppeteer", "webdriverio",
    "pytest", "unittest", "nose", "robot framework",
    "junit", "testng", "mockito", "spock",
    "rspec", "minitest", "capybara",
    "testing library", "react testing library", "enzyme",
    "postman", "insomnia", "swagger", "openapi",
    "load testing", "performance testing", "jmeter", "k6", "gatling",
    "code coverage", "mutation testing",
    "qa automation", "test automation", "manual testing",
    "regression testing", "smoke testing", "acceptance testing",
})

# ── Architecture & Design Patterns ────────────────────────────────────
ARCHITECTURE = frozenset({
    "microservices", "monolith", "serverless", "event-driven",
    "service-oriented architecture", "soa",
    "domain-driven design", "ddd",
    "cqrs", "event sourcing", "saga pattern",
    "rest", "restful", "graphql", "grpc", "protobuf",
    "websocket", "websockets", "sse", "server-sent events",
    "message queue", "rabbitmq", "activemq", "nats",
    "api design", "api gateway", "rate limiting",
    "caching", "cdn", "load balancing",
    "design patterns", "solid principles", "clean architecture",
    "hexagonal architecture", "mvc", "mvvm", "mvp",
    "system design", "distributed systems", "high availability",
    "scalability", "fault tolerance", "disaster recovery",
    "twelve-factor app", "12-factor",
})

# ── Methodologies & Practices ─────────────────────────────────────────
METHODOLOGIES = frozenset({
    "agile", "scrum", "kanban", "lean", "xp", "extreme programming",
    "sprint planning", "retrospective", "standup", "daily standup",
    "product owner", "scrum master",
    "waterfall", "v-model",
    "devops", "devsecops", "gitops", "platform engineering",
    "code review", "pair programming", "mob programming",
    "technical debt", "refactoring",
    "documentation", "technical writing",
    "version control", "branching strategy", "trunk-based development",
    "feature flags", "feature toggles", "canary deployment",
    "blue-green deployment", "rolling deployment",
    "incident management", "postmortem", "blameless postmortem",
    "on-call", "runbook",
})

# ── Soft Skills & Leadership ──────────────────────────────────────────
SOFT_SKILLS = frozenset({
    "leadership", "team leadership", "technical leadership",
    "mentoring", "coaching", "onboarding",
    "project management", "program management",
    "stakeholder management", "cross-functional collaboration",
    "communication", "presentation", "public speaking",
    "problem solving", "critical thinking", "analytical thinking",
    "time management", "prioritization",
    "decision making", "conflict resolution",
    "remote work", "distributed team",
})

# ── Tools & Platforms ─────────────────────────────────────────────────
TOOLS = frozenset({
    "jira", "confluence", "trello", "asana", "notion", "linear",
    "slack", "microsoft teams", "zoom",
    "vs code", "visual studio code", "intellij", "pycharm", "webstorm",
    "vim", "neovim", "emacs", "sublime text",
    "terminal", "command line", "cli",
    "postman", "insomnia", "curl", "httpie",
    "docker desktop", "lens", "k9s",
    "pgadmin", "dbeaver", "redis insight", "mongo compass",
    "sentry", "bugsnag", "rollbar",
    "segment", "amplitude", "mixpanel", "google analytics",
    "stripe", "twilio", "sendgrid", "auth0", "okta",
    "terraform cloud", "aws console",
})

# ── Union of all skills ───────────────────────────────────────────────
ALL_SKILLS: frozenset[str] = (
    LANGUAGES
    | FRONTEND
    | BACKEND
    | DATABASES
    | CLOUD
    | DEVOPS
    | DATA_SCIENCE
    | DATA_ENGINEERING
    | SECURITY
    | MOBILE
    | TESTING
    | ARCHITECTURE
    | METHODOLOGIES
    | SOFT_SKILLS
    | TOOLS
)


# ── Synonym / Acronym Normalization ──────────────────────────────────
# Maps abbreviations and variations to canonical full forms.
# The normalize_text() function expands abbreviations so that both forms
# appear in the text, ensuring ATS matching works regardless of which
# form the JD or resume uses.

TECH_SYNONYMS: dict[str, str] = {
    # Cloud providers
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "azure": "microsoft azure",
    # Container / orchestration
    "k8s": "kubernetes",
    "docker-compose": "docker compose",
    # AI / ML
    "ml": "machine learning",
    "dl": "deep learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "llm": "large language model",
    "gen ai": "generative ai",
    "rag": "retrieval augmented generation",
    "rlhf": "reinforcement learning from human feedback",
    # Languages
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "rb": "ruby",
    "cs": "c#",
    "cpp": "c++",
    "golang": "go",
    # Frameworks
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "next.js": "nextjs",
    "nest.js": "nestjs",
    "node.js": "nodejs",
    "express.js": "express",
    # Databases
    "postgres": "postgresql",
    "mongo": "mongodb",
    "mssql": "sql server",
    # DevOps / CI
    "ci/cd": "continuous integration continuous deployment",
    "iac": "infrastructure as code",
    "sre": "site reliability engineering",
    # Security
    "jwt": "json web token",
    "oauth2": "oauth",
    "oidc": "openid connect",
    "mfa": "multi-factor authentication",
    "2fa": "two-factor authentication",
    # Data
    "etl": "extract transform load",
    "elt": "extract load transform",
    # Testing
    "tdd": "test-driven development",
    "bdd": "behavior-driven development",
    "e2e": "end-to-end",
    # Methodologies
    "ddd": "domain-driven design",
    "cqrs": "command query responsibility segregation",
    "soa": "service-oriented architecture",
    # Other
    "api": "application programming interface",
    "sdk": "software development kit",
    "orm": "object-relational mapping",
    "cdn": "content delivery network",
    "dns": "domain name system",
    "vpc": "virtual private cloud",
    "ui": "user interface",
    "ux": "user experience",
    "qa": "quality assurance",
    "mvp": "minimum viable product",
    "poc": "proof of concept",
    "saas": "software as a service",
    "paas": "platform as a service",
    "iaas": "infrastructure as a service",
}

# Pre-compile regex patterns for word-boundary-aware replacement
_SYNONYM_PATTERNS: list[tuple[re.Pattern, str]] = []
for _abbr, _full in sorted(TECH_SYNONYMS.items(), key=lambda x: -len(x[0])):
    # Escape special regex chars in abbreviations (e.g., c++, c#, ci/cd)
    _SYNONYM_PATTERNS.append(
        (re.compile(rf"\b{re.escape(_abbr)}\b", re.IGNORECASE), _full)
    )


def normalize_text(text: str) -> str:
    """Expand abbreviations in text so both short and full forms are present.

    Example: "Experience with K8s and AWS" →
             "Experience with K8s kubernetes and AWS amazon web services"

    This helps scoring methods (BM25, TF-IDF, fuzzy) match regardless of
    which form (abbreviation or full name) appears in the JD vs resume.
    """
    lower = text.lower()
    expansions: list[str] = []
    for pattern, full_form in _SYNONYM_PATTERNS:
        if pattern.search(lower):
            # Check if the full form is already present
            if full_form not in lower:
                expansions.append(full_form)
    if expansions:
        return text + " " + " ".join(expansions)
    return text
