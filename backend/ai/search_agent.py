from uagents import Agent, Bureau, Context, Model
from backend.ai.semantic_search import SemanticSearch

class SearchRequest(Model):
    user_input: str

class SearchResponse(Model):
    end_node: dict
    confidence: float
    message: str

search_agent = Agent(
    name="end_node_search_agent",
    seed="end_node_search_agent_seed_phrase"
)

semantic_search = SemanticSearch()

@search_agent.on_message(model=SearchRequest)
async def handle_search(ctx: Context, sender: str, msg: SearchRequest):
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

bureau = Bureau()
bureau.add(search_agent)

if __name__ == "__main__":
    print("Starting End Node Search Agent...")
    bureau.run()
