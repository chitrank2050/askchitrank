"""Fictional seeded data used when DEV_MODE is enabled.

The goal is to keep local development productive without requiring
Voyage, Groq, Sanity, or real portfolio source files. The content is
small, stable, and intentionally representative of the production
domain so the API can still exercise realistic chat flows without
reusing the real portfolio identity.
"""

SEED_PERSON_NAME = "Avery Quinn"
SEED_CONTACT_EMAIL = "avery.quinn@example.dev"

SEED_RESUME_TEXT = """
Avery Quinn

Summary
Senior Software Engineer with 8+ years of experience building frontend
and full-stack products. Focused on React, TypeScript, Python, APIs,
and shipping polished developer and customer experiences.

Professional Experience
Built production web applications, internal tools, and AI-assisted
experiences across product, platform, and data-heavy workflows.
Led delivery across frontend architecture, API integrations, and
developer experience improvements.

Technical Skills
Languages: TypeScript, JavaScript, Python
Frameworks: React, Next.js, FastAPI
Platforms: PostgreSQL, Supabase, Sanity CMS
AI and Data: RAG, embeddings, prompt engineering, vector search
Tools: GitHub Actions, Docker, Vercel

Education
Bachelor of Technology in Computer Science
""".strip()


SEED_SANITY_PROJECTS = [
    {
        "_id": "seed-project-ask-avery",
        "title": "Ask Avery",
        "role": "Senior Software Engineer",
        "company": "Personal Project",
        "overview": (
            "Built a portfolio chatbot API that answers questions using resume, "
            "portfolio, and professional profile data."
        ),
        "vision": (
            "Make personal portfolio content searchable, grounded, and fast to "
            "explore with RAG."
        ),
        "technologies": [
            "FastAPI",
            "PostgreSQL",
            "pgvector",
            "Supabase",
            "TypeScript",
            "RAG",
        ],
        "contribution": [
            "Designed the ingestion, retrieval, and chat pipeline end to end.",
            "Added semantic caching and source-aware retrieval to reduce cost.",
            "Shaped the API for streaming responses and content re-ingestion.",
        ],
        "liveUrl": "https://example.dev/ask-avery",
        "githubUrl": "https://github.com/example/ask-avery",
    },
    {
        "_id": "seed-project-signal-canvas",
        "title": "Signal Canvas",
        "role": "Frontend and Full-stack Engineer",
        "company": "HealthTech",
        "overview": (
            "Delivered product experiences for a healthcare workflow tool with "
            "dashboards, data visualisation, and collaboration flows."
        ),
        "vision": (
            "Help teams act on operational and sensor-driven insights more quickly."
        ),
        "technologies": [
            "React",
            "TypeScript",
            "Python",
            "APIs",
            "Dashboards",
        ],
        "contribution": [
            "Implemented frontend architecture for data-heavy views.",
            "Worked closely with product stakeholders to improve usability.",
            "Integrated APIs and operational reporting features.",
        ],
        "liveUrl": "",
        "githubUrl": "",
    },
    {
        "_id": "seed-project-checkout-orbit",
        "title": "Checkout Orbit",
        "role": "Frontend Engineer",
        "company": "E-commerce",
        "overview": (
            "Built responsive checkout and account management flows focused on "
            "conversion and reliability."
        ),
        "vision": ("Create a smooth, trustworthy checkout experience across devices."),
        "technologies": [
            "React",
            "Next.js",
            "TypeScript",
            "A/B Testing",
            "Performance",
        ],
        "contribution": [
            "Improved critical user journeys on mobile and desktop.",
            "Shipped performance-focused frontend changes.",
            "Partnered with backend teams on API-driven checkout flows.",
        ],
        "liveUrl": "",
        "githubUrl": "",
    },
]


SEED_SANITY_TESTIMONIALS = [
    {
        "_id": "seed-testimonial-1",
        "author": "Aditi Sharma",
        "role": "Engineering Manager",
        "quote": (
            "Avery combines strong frontend craft with dependable delivery. "
            "He brings clarity to complex product work and communicates well "
            "with cross-functional teams."
        ),
        "linkedinUrl": "",
    },
    {
        "_id": "seed-testimonial-2",
        "author": "Rahul Mehta",
        "role": "Product Manager",
        "quote": (
            "He consistently turned ambiguous requirements into polished product "
            "experiences and was thoughtful about tradeoffs, user needs, and speed."
        ),
        "linkedinUrl": "",
    },
]


SEED_LINKEDIN_PROFILE = {
    "First Name": "Avery",
    "Last Name": "Quinn",
    "Headline": "Senior Software Engineer building frontend and full-stack products",
    "Summary": (
        "Experienced in React, TypeScript, Python, APIs, and shipping "
        "developer-friendly product experiences."
    ),
    "Industry": "Software Development",
    "Geo Location": "India",
    "Websites": "[PORTFOLIO:https://averyquinn.dev,GITHUB:https://github.com/example]",
}


SEED_LINKEDIN_RECOMMENDATIONS = [
    {
        "Status": "VISIBLE",
        "First Name": "Neha",
        "Last Name": "Kapoor",
        "Job Title": "Senior Designer",
        "Company": "Product Studio",
        "Text": (
            "Avery is collaborative, detail-oriented, and reliable under "
            "tight deadlines. He cares deeply about product quality."
        ),
    },
    {
        "Status": "VISIBLE",
        "First Name": "Aman",
        "Last Name": "Verma",
        "Job Title": "Engineering Lead",
        "Company": "Platform Team",
        "Text": (
            "He moves quickly without losing sight of maintainability and was "
            "great at aligning engineers around clean implementation details."
        ),
    },
]


def get_seeded_context_chunks() -> list[dict]:
    """Return a compact seeded context block for DB-free dev chat."""
    return [
        {
            "source": "resume",
            "content": (
                "Name: Avery Quinn\n"
                "Summary\n"
                "Senior Software Engineer with 8+ years of experience building "
                "frontend and full-stack products.\n"
                "Languages: TypeScript, JavaScript, Python\n"
                "Frameworks: React, Next.js, FastAPI"
            ),
        },
        {
            "source": "sanity",
            "content": (
                "Project: Ask Avery\n"
                "Technologies: FastAPI, PostgreSQL, pgvector, Supabase, RAG\n"
                "Overview: Built a portfolio chatbot API with semantic retrieval."
            ),
        },
        {
            "source": "testimonial",
            "content": (
                'Testimonial: "Avery combines strong frontend craft with dependable delivery."\n'
                "From: Aditi Sharma\n"
                "Role: Engineering Manager"
            ),
        },
    ]
