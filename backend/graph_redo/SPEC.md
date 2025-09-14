# AI-Powered Website Scraper & Knowledge Graph Builder

## Project Overview
An intelligent web scraper that navigates websites like a human user, creating a comprehensive knowledge graph of the site's structure, content, and interconnections using Neo4j graph database and OpenAI embeddings for semantic understanding.

## Technology Stack

### Core Technologies
- **Python 3.10+** - Primary programming language
- **Neo4j 5.x** - Graph database for storing website structure and relationships
- **OpenAI API** - For generating text embeddings (text-embedding-3-small/large)

### Web Scraping
- **Selenium** - Loading the JS and opening sessions
- **httpx** - HTTP library for fetching web pages
- **BeautifulSoup4** - HTML/XML parsing and navigation
- **urllib** - URL parsing and manipulation

### Data Processing
- **pandas** - Data manipulation and preprocessing
- **numpy** - Numerical operations for vector handling
- **python-dotenv** - Environment variable management

### API Framework (Future)
- **FastAPI** - Modern web framework for building APIs
- **uvicorn** - ASGI server for production deployment
- **pydantic** - Data validation and settings management

### Database
- **neo4j-python-driver** - Official Neo4j Python driver
- **py2neo** (optional) - Alternative higher-level Neo4j ORM

## Implementation Details

### 1. Crawler Architecture

#### URL Queue Management
- Maintain a queue of URLs to visit (BFS/DFS strategy configurable)
- Track visited URLs to avoid duplicates
- Implement domain boundary checking
- Handle URL normalization (remove fragments, normalize paths)

#### Page Processing Pipeline
1. **Fetch Stage**
   - Open the URL using selenium using pre-existing profile to preserve logged in sessions. 
   - Get the website content
   - Handle redirects (301, 302, etc.)
   - Capture HTTP status codes
   - Record response time
   - Handle timeouts and retries

2. **Parse Stage**
   - Extract HTML content using BeautifulSoup
   - Identify all clickable elements:
     - `<a>` tags with href attributes
     - `<button>` elements with onclick or data attributes
     - Form submission buttons
     - JavaScript navigation elements (marked for future enhancement)

3. **Content Extraction**
   - Page title from `<title>` tag
   - Meta descriptions and keywords
   - Main content text (cleaned of scripts/styles)
   - Structured data (JSON-LD, microdata if present)
   - Image alt texts
   - Header hierarchy (h1-h6)

4. **Vectorization Stage**
   - Concatenate relevant text content
   - Clean and preprocess text
   - Generate embeddings via OpenAI API
   - Store vectors with appropriate metadata

5. **Storage Stage**
   - Create/update Neo4j node for current URL
   - Create relationships to linked pages
   - Store external links as separate node type
   - Update crawl timestamp

### 2. Neo4j Graph Schema

#### Node Types

**Page Node**
```cypher
(:Page {
    url: STRING (unique),
    domain: STRING,
    path: STRING,
    title: STRING,
    meta_description: STRING,
    content_text: TEXT,
    content_vector: LIST<FLOAT>,
    http_status: INTEGER,
    response_time_ms: FLOAT,
    first_crawled: DATETIME,
    last_crawled: DATETIME,
    content_hash: STRING
})
```

**ExternalLink Node**
```cypher
(:ExternalLink {
    url: STRING (unique),
    domain: STRING,
    first_seen: DATETIME,
    reference_count: INTEGER
})
```

**Element Node** (for detailed UI elements tracking)
```cypher
(:Element {
    id: STRING,
    type: STRING, // 'link', 'button', 'form'
    text: STRING,
    attributes: MAP,
    selector: STRING
})
```

#### Relationship Types
- `(:Page)-[:LINKS_TO]->(:Page)` - Internal navigation
- `(:Page)-[:LINKS_TO_EXTERNAL]->(:ExternalLink)` - External references
- `(:Page)-[:HAS_ELEMENT]->(:Element)` - UI element ownership
- `(:Element)-[:NAVIGATES_TO]->(:Page)` - Element navigation target
- `(:Page)-[:SIMILAR_TO {score: FLOAT}]->(:Page)` - Semantic similarity (computed from vectors)

### 3. Crawling Strategy


#### Boundary Rules
- Stay within same domain (configurable for subdomains)
- Maximum depth limit (default: 10 levels)
- Maximum pages per crawl session (default: 1000)
- External link detection and storage without following

### 4. Vector Search & Similarity

#### Embedding Generation
- Use OpenAI's text-embedding-3-small for MVP
- Batch API calls for efficiency
- Cache embeddings to avoid re-computation
- Fallback handling for API failures

#### Similarity Computation
- Cosine similarity for vector comparison
- Create similarity relationships above threshold
- Enable semantic search queries
- Support for finding related content

## Functions and Information

### Core Functions

#### `WebCrawler` Class
```python
class WebCrawler:
    def __init__(self, neo4j_uri, neo4j_auth, openai_api_key, base_url)
    def crawl(self, max_pages=1000, max_depth=10)
    def fetch_page(self, url) -> dict
    def parse_page(self, html_content, base_url) -> dict
    def extract_links(self, soup, base_url) -> list
    def extract_content(self, soup) -> dict
    def generate_embedding(self, text) -> list
    def store_to_neo4j(self, page_data, links_data)
    def is_valid_url(self, url) -> bool
    def should_crawl(self, url) -> bool
    def update_queue(self, new_urls)
```

#### `Neo4jManager` Class
```python
class Neo4jManager:
    def __init__(self, uri, auth)
    def create_page_node(self, page_data) -> str
    def create_relationship(self, from_url, to_url, rel_type)
    def update_page_node(self, url, updates)
    def find_similar_pages(self, vector, threshold=0.8) -> list
    def get_page_graph(self, url, depth=2) -> dict
    def execute_query(self, cypher_query, parameters=None)
```

#### `ContentProcessor` Class
```python
class ContentProcessor:
    def __init__(self, openai_api_key)
    def generate_summary(self, text) -> str
    def create_embedding(self, text) -> list
```

#### Utility Functions
```python
def normalize_url(url) -> str
def is_external_link(url, base_domain) -> bool
def calculate_similarity(vector1, vector2) -> float
def extract_domain(url) -> str
def hash_content(content) -> str
```

### API Endpoints (Future)

```python
POST   /crawl/start        - Initiate crawling session
GET    /crawl/status/{id}  - Get crawl job status
POST   /crawl/stop/{id}    - Stop active crawl
GET    /graph/node/{url}   - Get node information
GET    /graph/similar      - Find similar pages
GET    /graph/path         - Find path between pages
GET    /graph/structure    - Get site structure
POST   /search/semantic    - Semantic search in graph
GET    /stats/overview     - Crawl statistics
```

## Architecture Diagram

```ascii
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI-Powered Web Scraper System                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   INPUT      │      │   CRAWLER    │      │   STORAGE    │
│              │      │   ENGINE     │      │              │
│  Landing URL │─────>│              │      │   Neo4j DB   │
│              │      │  URL Queue   │─────>│              │
└──────────────┘      │              │      │  ┌────────┐ │
                      │  Fetcher     │      │  │ Nodes  │ │
                      │      ↓       │      │  └────────┘ │
┌──────────────┐      │  Parser      │      │  ┌────────┐ │
│   EXTERNAL   │      │      ↓       │      │  │ Edges  │ │
│   SERVICES   │      │  Extractor   │      │  └────────┘ │
│              │      │      ↓       │      │  ┌────────┐ │
│  OpenAI API  │<─────│  Embedder    │      │  │Vectors │ │
│              │      │      ↓       │      │  └────────┘ │
└──────────────┘      │  Storage     │─────>│              │
                      │  Handler     │      └──────────────┘
                      └──────────────┘
                             ↑
                             │
                      ┌──────────────┐
                      │   CONTROL    │
                      │              │
                      │ Rate Limiter │
                      │ URL Filter   │
                      │ Deduplicator │
                      └──────────────┘

Data Flow:
═════════
1. URL Input ──> Queue Manager ──> Fetcher
2. Fetcher ──> HTML Response ──> Parser
3. Parser ──> Extracted Data ──> Content Processor
4. Content ──> OpenAI API ──> Embeddings
5. Extracted Data + Embeddings ──> Neo4j Storage
6. New URLs ──> URL Filter ──> Queue Manager (Loop)

Neo4j Graph Structure:
═════════════════════
        ┌────────┐
        │  Page  │◄────────LINKS_TO────────┐
        │   /    │                          │
        └───┬────┘                     ┌────────┐
            │                          │  Page  │
            │HAS_ELEMENT               │ /about │
            ↓                          └────────┘
        ┌────────┐                          ↑
        │Element │                          │
        │ Button │──────NAVIGATES_TO───────┘
        └────────┘

        ┌────────┐      LINKS_TO_EXTERNAL    ┌──────────┐
        │  Page  │─────────────────────────>│ External │
        │/contact│                          │   Link   │
        └────────┘                          └──────────┘
```

## Additional Notes

### MVP Limitations
3. **Single Domain Focus** - External links noted but not followed
4. **Basic Robot Detection** - May be blocked by sophisticated anti-bot measures

### Future Enhancements

#### Phase 2: Dynamic Content
- Integrate Selenium/Playwright for JavaScript rendering
- Handle SPAs (Single Page Applications)
- Capture AJAX requests and dynamic content loading
- Screenshot capability for visual analysis

#### Phase 3: Authentication & Sessions
- Support for basic auth, form-based login
- Cookie management and session persistence
- OAuth flow handling
- Multi-step authentication processes

#### Phase 4: Advanced Intelligence
- Natural language queries on graph data
- Automatic site map generation
- Content change detection and monitoring
- Intelligent crawl prioritization based on importance
- Multi-modal analysis (images, videos)

#### Phase 5: Scalability
- Distributed crawling with multiple workers
- Redis queue for distributed URL management
- Kubernetes deployment for horizontal scaling
- Graph partitioning for large datasets
- Real-time streaming updates

### Performance Considerations
- **Connection Pooling**: Maintain persistent Neo4j connections
- **Caching Strategy**: Cache embeddings and frequently accessed nodes
- **Indexing**: Create indexes on url, domain, and vector fields
- **Async Operations**: Use asyncio for concurrent page fetching



### Monitoring & Logging
- Crawl progress tracking
- Error logging with context
- Performance metrics (pages/second, API usage)
- Neo4j query performance monitoring
- Alerting for failures or anomalies

### Testing Strategy
- Unit tests for individual components
- Integration tests for crawl pipeline
- Mock external services (OpenAI, web requests)
- Graph consistency validation
- Performance benchmarking
