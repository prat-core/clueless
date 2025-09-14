from uagents import Agent, Bureau, Context, Model
from semantic_search import SemanticSearch

class SearchRequest(Model):
    user_input: str

class SearchResponse(Model):
    end_node: dict
    confidence: float
    message: str

class SimilarNodesRequest(Model):
    search_query: str
    limit: int = 5

class SimilarNodesResponse(Model):
    similar_nodes: list
    message: str

search_agent = Agent(
    name="end_node_search_agent",
    seed="end_node_search_agent_seed_phrase_v3",
    mailbox=True,
)

semantic_search = SemanticSearch()

@search_agent.on_message(model=SearchRequest)
async def handle_search(ctx: Context, sender: str, msg: SearchRequest):
    """Handle end node search requests using consolidated semantic search"""
    ctx.logger.info(f"Searching for end node: '{msg.user_input}'")
    
    try:
        result = semantic_search.find_end_node(msg.user_input)
        response = SearchResponse(
            end_node=result["end_node"],
            confidence=result["confidence"],
            message=result["message"]
        )
        await ctx.send(sender, response)
    except Exception as e:
        ctx.logger.error(f"Error: {e}")
        error_response = SearchResponse(
            end_node=None,
            confidence=0.0,
            message=f"Error: {str(e)}"
        )
        await ctx.send(sender, error_response)

@search_agent.on_message(model=SimilarNodesRequest)
async def handle_similar_nodes(ctx: Context, sender: str, msg: SimilarNodesRequest):
    """Handle similar nodes search requests using consolidated semantic search"""
    ctx.logger.info(f"Searching for similar nodes: '{msg.search_query}'")
    
    try:
        similar_nodes = semantic_search.find_similar_nodes(msg.search_query, msg.limit)
        response = SimilarNodesResponse(
            similar_nodes=similar_nodes,
            message=f"Found {len(similar_nodes)} similar nodes"
        )
        await ctx.send(sender, response)
    except Exception as e:
        ctx.logger.error(f"Error: {e}")
        error_response = SimilarNodesResponse(
            similar_nodes=[],
            message=f"Error: {str(e)}"
        )
        await ctx.send(sender, error_response)

bureau = Bureau()
bureau.add(search_agent)

if __name__ == "__main__":
    print("Starting End Node Search Agent...")
    bureau.run()
