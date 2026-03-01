"""Curated technology skills taxonomy for ATS skill-coverage scoring.

Organized by category. Each category is a frozenset of lowercase canonical skill names.
ALL_SKILLS is the union used by the PhraseMatcher in the scorer.

TECH_SYNONYMS maps abbreviations/variations to their canonical forms, enabling
the scorer to treat "K8s" and "Kubernetes" as the same skill.

Chinese ATS support:
- ACTION_VERBS_ZH_STRONG/MEDIUM/WEAK: tiered Chinese action verbs
- EXPECTED_SECTIONS_ZH: Chinese resume section name variants
- SKILL_ALIASES_ZH: bilingual skill mapping (Chinese <-> English canonical)
"""

import re

# ── Programming Languages ─────────────────────────────────────────────
LANGUAGES = frozenset(
    {
        "python",
        "java",
        "javascript",
        "typescript",
        "c",
        "c++",
        "c#",
        "go",
        "golang",
        "rust",
        "ruby",
        "php",
        "swift",
        "kotlin",
        "scala",
        "r",
        "matlab",
        "perl",
        "lua",
        "haskell",
        "erlang",
        "elixir",
        "objective-c",
        "dart",
        "groovy",
        "clojure",
        "f#",
        "julia",
        "assembly",
        "vhdl",
        "verilog",
        "cobol",
        "fortran",
        "lisp",
        "scheme",
        "ocaml",
        "zig",
        "nim",
        "crystal",
        "solidity",
        "bash",
        "shell",
        "powershell",
        "sql",
        "plsql",
        "t-sql",
        "html",
        "css",
        "sass",
        "scss",
        "less",
    }
)

# ── Frontend Frameworks & Libraries ───────────────────────────────────
FRONTEND = frozenset(
    {
        "react",
        "reactjs",
        "react.js",
        "angular",
        "angularjs",
        "vue",
        "vue.js",
        "vuejs",
        "svelte",
        "next.js",
        "nextjs",
        "nuxt",
        "nuxt.js",
        "gatsby",
        "remix",
        "astro",
        "solid.js",
        "solidjs",
        "jquery",
        "backbone.js",
        "ember.js",
        "preact",
        "lit",
        "alpine.js",
        "htmx",
        "stimulus",
        "turbo",
        "redux",
        "zustand",
        "mobx",
        "recoil",
        "jotai",
        "xstate",
        "react query",
        "tanstack query",
        "swr",
        "tailwind",
        "tailwindcss",
        "tailwind css",
        "bootstrap",
        "material ui",
        "mui",
        "chakra ui",
        "ant design",
        "shadcn",
        "styled-components",
        "emotion",
        "css modules",
        "webpack",
        "vite",
        "rollup",
        "esbuild",
        "parcel",
        "turbopack",
        "storybook",
        "figma",
        "sketch",
        "adobe xd",
        "three.js",
        "d3.js",
        "d3",
        "chart.js",
        "echarts",
    }
)

# ── Backend Frameworks ────────────────────────────────────────────────
BACKEND = frozenset(
    {
        "node.js",
        "nodejs",
        "node",
        "express",
        "express.js",
        "fastify",
        "nest.js",
        "nestjs",
        "koa",
        "hapi",
        "django",
        "flask",
        "fastapi",
        "tornado",
        "celery",
        "gunicorn",
        "uvicorn",
        "starlette",
        "aiohttp",
        "spring",
        "spring boot",
        "spring framework",
        "quarkus",
        "micronaut",
        "hibernate",
        "maven",
        "gradle",
        "ruby on rails",
        "rails",
        "sinatra",
        "asp.net",
        ".net",
        ".net core",
        "blazor",
        "entity framework",
        "laravel",
        "symfony",
        "codeigniter",
        "gin",
        "echo",
        "fiber",
        "chi",
        "phoenix",
        "actix",
        "axum",
        "rocket",
    }
)

# ── Databases ─────────────────────────────────────────────────────────
DATABASES = frozenset(
    {
        "postgresql",
        "postgres",
        "mysql",
        "mariadb",
        "sqlite",
        "oracle",
        "sql server",
        "mssql",
        "db2",
        "mongodb",
        "mongoose",
        "couchdb",
        "couchbase",
        "redis",
        "memcached",
        "valkey",
        "elasticsearch",
        "opensearch",
        "solr",
        "lucene",
        "cassandra",
        "dynamodb",
        "scylla",
        "hbase",
        "neo4j",
        "arangodb",
        "dgraph",
        "neptune",
        "influxdb",
        "timescaledb",
        "clickhouse",
        "druid",
        "snowflake",
        "bigquery",
        "redshift",
        "databricks",
        "cockroachdb",
        "tidb",
        "yugabytedb",
        "planetscale",
        "supabase",
        "firebase",
        "firestore",
        "prisma",
        "typeorm",
        "sequelize",
        "sqlalchemy",
        "knex",
    }
)

# ── Cloud Platforms & Services ────────────────────────────────────────
CLOUD = frozenset(
    {
        "aws",
        "amazon web services",
        "ec2",
        "s3",
        "lambda",
        "ecs",
        "eks",
        "fargate",
        "rds",
        "aurora",
        "dynamodb",
        "sqs",
        "sns",
        "kinesis",
        "cloudformation",
        "cdk",
        "cloudwatch",
        "iam",
        "route 53",
        "cloudfront",
        "api gateway",
        "step functions",
        "sagemaker",
        "bedrock",
        "glue",
        "athena",
        "emr",
        "azure",
        "microsoft azure",
        "azure devops",
        "azure functions",
        "azure kubernetes service",
        "aks",
        "azure blob storage",
        "azure sql",
        "azure cosmos db",
        "azure pipelines",
        "gcp",
        "google cloud",
        "google cloud platform",
        "compute engine",
        "cloud run",
        "cloud functions",
        "gke",
        "cloud storage",
        "cloud sql",
        "pub/sub",
        "dataflow",
        "vertex ai",
        "cloud build",
        "heroku",
        "vercel",
        "netlify",
        "render",
        "fly.io",
        "digitalocean",
        "linode",
        "vultr",
        "cloudflare",
        "cloudflare workers",
        "cloudflare pages",
    }
)

# ── DevOps, CI/CD & Infrastructure ───────────────────────────────────
DEVOPS = frozenset(
    {
        "docker",
        "dockerfile",
        "docker compose",
        "docker-compose",
        "kubernetes",
        "k8s",
        "helm",
        "kustomize",
        "istio",
        "linkerd",
        "openshift",
        "rancher",
        "terraform",
        "pulumi",
        "ansible",
        "chef",
        "puppet",
        "saltstack",
        "vagrant",
        "packer",
        "jenkins",
        "github actions",
        "gitlab ci",
        "circleci",
        "travis ci",
        "buildkite",
        "argo cd",
        "argocd",
        "flux",
        "spinnaker",
        "tekton",
        "drone",
        "prometheus",
        "grafana",
        "datadog",
        "new relic",
        "splunk",
        "elk stack",
        "logstash",
        "kibana",
        "jaeger",
        "zipkin",
        "pagerduty",
        "opsgenie",
        "nginx",
        "apache",
        "caddy",
        "envoy",
        "haproxy",
        "traefik",
        "consul",
        "vault",
        "etcd",
        "zookeeper",
        "git",
        "github",
        "gitlab",
        "bitbucket",
        "mercurial",
        "linux",
        "unix",
        "ubuntu",
        "centos",
        "rhel",
        "debian",
        "windows server",
        "macos",
        "ci/cd",
        "continuous integration",
        "continuous deployment",
        "continuous delivery",
        "infrastructure as code",
        "iac",
        "site reliability engineering",
        "sre",
        "observability",
        "monitoring",
        "logging",
        "alerting",
    }
)

# ── Data Science & Machine Learning ──────────────────────────────────
DATA_SCIENCE = frozenset(
    {
        "machine learning",
        "deep learning",
        "artificial intelligence",
        "ai",
        "neural network",
        "nlp",
        "natural language processing",
        "computer vision",
        "reinforcement learning",
        "tensorflow",
        "pytorch",
        "keras",
        "jax",
        "mxnet",
        "scikit-learn",
        "sklearn",
        "xgboost",
        "lightgbm",
        "catboost",
        "pandas",
        "numpy",
        "scipy",
        "matplotlib",
        "seaborn",
        "plotly",
        "jupyter",
        "jupyter notebook",
        "colab",
        "hugging face",
        "huggingface",
        "transformers",
        "bert",
        "gpt",
        "llm",
        "large language model",
        "langchain",
        "langgraph",
        "rag",
        "retrieval augmented generation",
        "prompt engineering",
        "fine-tuning",
        "rlhf",
        "opencv",
        "yolo",
        "detectron",
        "stable diffusion",
        "mlflow",
        "wandb",
        "weights and biases",
        "dvc",
        "feature engineering",
        "model deployment",
        "mlops",
        "a/b testing",
        "statistical analysis",
        "hypothesis testing",
        "regression",
        "classification",
        "clustering",
        "random forest",
        "gradient boosting",
        "svm",
        "knn",
        "cnn",
        "rnn",
        "lstm",
        "transformer",
        "attention mechanism",
        "generative ai",
        "gen ai",
    }
)

# ── Data Engineering & Big Data ───────────────────────────────────────
DATA_ENGINEERING = frozenset(
    {
        "apache spark",
        "spark",
        "pyspark",
        "apache kafka",
        "kafka",
        "kafka streams",
        "apache flink",
        "flink",
        "apache airflow",
        "airflow",
        "dagster",
        "prefect",
        "luigi",
        "apache beam",
        "dataflow",
        "hadoop",
        "hdfs",
        "mapreduce",
        "hive",
        "pig",
        "presto",
        "trino",
        "dbt",
        "data build tool",
        "etl",
        "elt",
        "data pipeline",
        "data warehouse",
        "data lake",
        "data lakehouse",
        "delta lake",
        "iceberg",
        "hudi",
        "data modeling",
        "dimensional modeling",
        "star schema",
        "data governance",
        "data quality",
        "data catalog",
        "fivetran",
        "airbyte",
        "stitch",
        "talend",
        "looker",
        "tableau",
        "power bi",
        "metabase",
        "superset",
        "snowflake",
        "bigquery",
        "redshift",
        "databricks",
    }
)

# ── Security ──────────────────────────────────────────────────────────
SECURITY = frozenset(
    {
        "cybersecurity",
        "information security",
        "infosec",
        "penetration testing",
        "pen testing",
        "ethical hacking",
        "vulnerability assessment",
        "threat modeling",
        "soc",
        "security operations center",
        "siem",
        "soar",
        "ids",
        "ips",
        "oauth",
        "oauth2",
        "openid connect",
        "oidc",
        "saml",
        "jwt",
        "json web token",
        "api key",
        "mfa",
        "2fa",
        "ssl",
        "tls",
        "https",
        "encryption",
        "pki",
        "owasp",
        "cve",
        "zero trust",
        "firewall",
        "waf",
        "vpn",
        "ipsec",
        "compliance",
        "gdpr",
        "hipaa",
        "soc 2",
        "pci dss",
        "iso 27001",
        "devsecops",
        "sast",
        "dast",
        "container security",
    }
)

# ── Mobile Development ────────────────────────────────────────────────
MOBILE = frozenset(
    {
        "ios",
        "android",
        "mobile development",
        "react native",
        "flutter",
        "xamarin",
        "ionic",
        "cordova",
        "swiftui",
        "uikit",
        "jetpack compose",
        "android studio",
        "xcode",
        "cocoapods",
        "carthage",
        "spm",
        "expo",
        "capacitor",
        "app store",
        "google play",
        "testflight",
        "push notifications",
        "deep linking",
        "mobile testing",
        "appium",
        "detox",
    }
)

# ── Testing & QA ──────────────────────────────────────────────────────
TESTING = frozenset(
    {
        "unit testing",
        "integration testing",
        "end-to-end testing",
        "e2e testing",
        "test-driven development",
        "tdd",
        "behavior-driven development",
        "bdd",
        "jest",
        "mocha",
        "chai",
        "jasmine",
        "vitest",
        "cypress",
        "playwright",
        "selenium",
        "puppeteer",
        "webdriverio",
        "pytest",
        "unittest",
        "nose",
        "robot framework",
        "junit",
        "testng",
        "mockito",
        "spock",
        "rspec",
        "minitest",
        "capybara",
        "testing library",
        "react testing library",
        "enzyme",
        "postman",
        "insomnia",
        "swagger",
        "openapi",
        "load testing",
        "performance testing",
        "jmeter",
        "k6",
        "gatling",
        "code coverage",
        "mutation testing",
        "qa automation",
        "test automation",
        "manual testing",
        "regression testing",
        "smoke testing",
        "acceptance testing",
    }
)

# ── Architecture & Design Patterns ────────────────────────────────────
ARCHITECTURE = frozenset(
    {
        "microservices",
        "monolith",
        "serverless",
        "event-driven",
        "service-oriented architecture",
        "soa",
        "domain-driven design",
        "ddd",
        "cqrs",
        "event sourcing",
        "saga pattern",
        "rest",
        "restful",
        "graphql",
        "grpc",
        "protobuf",
        "websocket",
        "websockets",
        "sse",
        "server-sent events",
        "message queue",
        "rabbitmq",
        "activemq",
        "nats",
        "api design",
        "api gateway",
        "rate limiting",
        "caching",
        "cdn",
        "load balancing",
        "design patterns",
        "solid principles",
        "clean architecture",
        "hexagonal architecture",
        "mvc",
        "mvvm",
        "mvp",
        "system design",
        "distributed systems",
        "high availability",
        "scalability",
        "fault tolerance",
        "disaster recovery",
        "twelve-factor app",
        "12-factor",
    }
)

# ── Methodologies & Practices ─────────────────────────────────────────
METHODOLOGIES = frozenset(
    {
        "agile",
        "scrum",
        "kanban",
        "lean",
        "xp",
        "extreme programming",
        "sprint planning",
        "retrospective",
        "standup",
        "daily standup",
        "product owner",
        "scrum master",
        "waterfall",
        "v-model",
        "devops",
        "devsecops",
        "gitops",
        "platform engineering",
        "code review",
        "pair programming",
        "mob programming",
        "technical debt",
        "refactoring",
        "documentation",
        "technical writing",
        "version control",
        "branching strategy",
        "trunk-based development",
        "feature flags",
        "feature toggles",
        "canary deployment",
        "blue-green deployment",
        "rolling deployment",
        "incident management",
        "postmortem",
        "blameless postmortem",
        "on-call",
        "runbook",
    }
)

# ── Soft Skills & Leadership ──────────────────────────────────────────
SOFT_SKILLS = frozenset(
    {
        "leadership",
        "team leadership",
        "technical leadership",
        "mentoring",
        "coaching",
        "onboarding",
        "project management",
        "program management",
        "stakeholder management",
        "cross-functional collaboration",
        "communication",
        "presentation",
        "public speaking",
        "problem solving",
        "critical thinking",
        "analytical thinking",
        "time management",
        "prioritization",
        "decision making",
        "conflict resolution",
        "remote work",
        "distributed team",
    }
)

# ── Tools & Platforms ─────────────────────────────────────────────────
TOOLS = frozenset(
    {
        "jira",
        "confluence",
        "trello",
        "asana",
        "notion",
        "linear",
        "slack",
        "microsoft teams",
        "zoom",
        "vs code",
        "visual studio code",
        "intellij",
        "pycharm",
        "webstorm",
        "vim",
        "neovim",
        "emacs",
        "sublime text",
        "terminal",
        "command line",
        "cli",
        "postman",
        "insomnia",
        "curl",
        "httpie",
        "docker desktop",
        "lens",
        "k9s",
        "pgadmin",
        "dbeaver",
        "redis insight",
        "mongo compass",
        "sentry",
        "bugsnag",
        "rollbar",
        "segment",
        "amplitude",
        "mixpanel",
        "google analytics",
        "stripe",
        "twilio",
        "sendgrid",
        "auth0",
        "okta",
        "terraform cloud",
        "aws console",
    }
)

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
    _SYNONYM_PATTERNS.append((re.compile(rf"\b{re.escape(_abbr)}\b", re.IGNORECASE), _full))


# ── Chinese Action Verbs (tiered by ATS impact) ─────────────────────
# Strong verbs demonstrate leadership, ownership, and measurable impact.
# Medium verbs indicate competence. Weak verbs suggest limited ownership.

ACTION_VERBS_ZH_STRONG = frozenset(
    {
        "主导",
        "设计",
        "架构",
        "推动",
        "优化",
        "重构",
        "攻克",
        "带领",
        "建立",
        "制定",
        "搭建",
        "构建",
        "研发",
        "创建",
        "引入",
        "落地",
        "交付",
        "革新",
        "统筹",
        "规划",
        "牵头",
        "孵化",
        "打造",
        "赋能",
        "突破",
    }
)

ACTION_VERBS_ZH_MEDIUM = frozenset(
    {
        "负责",
        "完成",
        "实现",
        "开发",
        "维护",
        "部署",
        "迁移",
        "整合",
        "测试",
        "编写",
        "管理",
        "协调",
        "推进",
        "支撑",
        "保障",
        "提升",
        "改进",
        "调优",
        "封装",
        "对接",
    }
)

ACTION_VERBS_ZH_WEAK = frozenset(
    {
        "参与",
        "配合",
        "协助",
        "了解",
        "学习",
        "接触",
        "跟进",
        "熟悉",
        "使用",
        "运用",
    }
)

ACTION_VERBS_ZH_ALL = ACTION_VERBS_ZH_STRONG | ACTION_VERBS_ZH_MEDIUM | ACTION_VERBS_ZH_WEAK


# ── Chinese Expected Sections (with common variants) ────────────────
# Maps canonical section name to list of variant names found in resumes.

EXPECTED_SECTIONS_ZH: dict[str, list[str]] = {
    "教育": ["教育背景", "教育经历", "学历", "学业"],
    "工作": ["工作经历", "工作经验", "职业经历", "从业经历"],
    "项目": ["项目经历", "项目经验", "项目描述", "项目成果"],
    "技能": ["专业技能", "技能特长", "技术技能", "技术栈", "核心技能"],
    "自我评价": ["自我评价", "个人总结", "个人简介", "自我介绍", "个人优势"],
    "获奖": ["获奖情况", "荣誉奖项", "证书", "资质证书", "荣誉与奖励"],
}

# Flat set of all Chinese section name variants for quick matching
ALL_SECTION_NAMES_ZH = frozenset(
    name for variants in EXPECTED_SECTIONS_ZH.values() for name in variants
) | frozenset(EXPECTED_SECTIONS_ZH.keys())


# ── Bilingual Skill Aliases (Chinese <-> English) ───────────────────
# Maps Chinese canonical skill name to list of aliases (English, abbreviations, variants).
# Used by the ATS scorer to normalize bilingual resumes/JDs.

SKILL_ALIASES_ZH: dict[str, list[str]] = {
    # AI / ML
    "机器学习": ["ML", "Machine Learning", "机器学习算法"],
    "深度学习": ["Deep Learning", "DL", "神经网络"],
    "自然语言处理": ["NLP", "Natural Language Processing", "文本处理", "文本挖掘"],
    "计算机视觉": ["CV", "Computer Vision", "图像识别", "图像处理"],
    "人工智能": ["AI", "Artificial Intelligence", "智能算法"],
    "大语言模型": ["LLM", "Large Language Model", "大模型"],
    "生成式AI": ["Generative AI", "Gen AI", "AIGC"],
    "强化学习": ["Reinforcement Learning", "RL"],
    "推荐系统": ["Recommendation System", "推荐算法", "推荐引擎"],
    "知识图谱": ["Knowledge Graph", "KG"],
    "语音识别": ["ASR", "Speech Recognition"],
    "目标检测": ["Object Detection", "YOLO", "目标识别"],
    # Frontend
    "前端开发": ["前端", "Frontend", "Web前端", "FE", "前端工程师"],
    "后端开发": ["后端", "Backend", "服务端开发", "BE", "后端工程师"],
    "全栈开发": ["Full Stack", "全栈", "全栈工程师"],
    "移动开发": ["Mobile Development", "移动端开发", "App开发"],
    "小程序": ["Mini Program", "微信小程序", "支付宝小程序"],
    "响应式设计": ["Responsive Design", "自适应布局"],
    # Architecture
    "微服务": ["Microservice", "微服务架构", "Microservices"],
    "分布式系统": ["Distributed System", "分布式架构"],
    "高并发": ["High Concurrency", "高并发系统", "高并发架构"],
    "高可用": ["High Availability", "HA", "高可用架构"],
    "服务网格": ["Service Mesh", "Istio", "服务网格架构"],
    "中间件": ["Middleware", "消息中间件"],
    "网关": ["API Gateway", "网关服务"],
    # DevOps / Infra
    "容器化": ["Docker", "容器", "容器技术"],
    "容器编排": ["Kubernetes", "K8s", "编排", "容器编排技术"],
    "持续集成": ["CI", "Continuous Integration"],
    "持续部署": ["CD", "Continuous Deployment", "Continuous Delivery"],
    "自动化运维": ["DevOps", "SRE", "运维自动化"],
    "基础设施即代码": ["IaC", "Infrastructure as Code", "Terraform"],
    "监控告警": ["Monitoring", "Alerting", "可观测性", "Observability"],
    # Data
    "消息队列": ["MQ", "Message Queue", "Kafka", "RabbitMQ", "RocketMQ"],
    "关系型数据库": ["RDBMS", "MySQL", "PostgreSQL", "Oracle", "SQL Server"],
    "缓存": ["Redis", "Memcached", "缓存技术"],
    "搜索引擎": ["Elasticsearch", "ES", "Solr", "搜索技术"],
    "大数据": ["Big Data", "大数据处理", "大数据技术"],
    "数据仓库": ["Data Warehouse", "数仓", "Hive", "数据仓库建设"],
    "数据湖": ["Data Lake", "数据湖架构"],
    "实时计算": ["Stream Processing", "Flink", "实时数据处理", "流计算"],
    "数据分析": ["Data Analysis", "数据挖掘", "BI", "数据分析师"],
    "ETL": ["数据集成", "数据抽取", "Extract Transform Load"],
    "数据治理": ["Data Governance", "数据质量", "数据管理"],
    # Cloud
    "云计算": ["Cloud Computing", "云服务", "云平台"],
    "阿里云": ["Alibaba Cloud", "Aliyun"],
    "腾讯云": ["Tencent Cloud"],
    "华为云": ["Huawei Cloud"],
    "云原生": ["Cloud Native", "云原生架构"],
    "无服务器": ["Serverless", "函数计算", "FaaS"],
    # Security
    "网络安全": ["Cybersecurity", "Information Security", "信息安全"],
    "渗透测试": ["Penetration Testing", "Pen Testing"],
    "安全审计": ["Security Audit", "安全合规"],
    "身份认证": ["Authentication", "Auth", "身份验证"],
    "权限管理": ["Authorization", "RBAC", "权限控制"],
    # Testing
    "单元测试": ["Unit Testing", "单测"],
    "集成测试": ["Integration Testing"],
    "自动化测试": ["Test Automation", "自动化测试框架"],
    "性能测试": ["Performance Testing", "压力测试", "Load Testing"],
    # Methodologies
    "敏捷开发": ["Agile", "Scrum", "敏捷"],
    "项目管理": ["Project Management", "PM"],
    "技术评审": ["Code Review", "技术审查", "代码评审"],
    "需求分析": ["Requirement Analysis", "需求评审"],
    "系统设计": ["System Design", "架构设计"],
    "技术方案": ["Technical Design", "方案设计"],
    # Soft skills
    "团队管理": ["Team Management", "团队建设", "带团队"],
    "跨部门协作": ["Cross-functional Collaboration", "跨团队协作"],
    "技术分享": ["Tech Talk", "技术布道"],
    "文档编写": ["Technical Writing", "文档能力"],
}

# Build reverse lookup: English/alias -> Chinese canonical
_SKILL_ALIAS_REVERSE_ZH: dict[str, str] = {}
for _zh_canonical, _aliases in SKILL_ALIASES_ZH.items():
    for _alias in _aliases:
        _SKILL_ALIAS_REVERSE_ZH[_alias.lower()] = _zh_canonical


def normalize_skill_zh(skill: str) -> str:
    """Normalize a skill name using the Chinese bilingual alias map.

    Returns the Chinese canonical form if found, otherwise the original.
    """
    if skill in SKILL_ALIASES_ZH:
        return skill
    return _SKILL_ALIAS_REVERSE_ZH.get(skill.lower(), skill)


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
