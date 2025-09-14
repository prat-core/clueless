#!/usr/bin/env python3
"""
Test script to verify Neo4j integration with Neo4jManager
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def test_neo4j_processor():
    """Test the neo4j_processor with Neo4jManager integration"""
    print("=" * 60)
    print("Testing neo4j_processor with Neo4jManager")
    print("=" * 60)
    
    try:
        from ai.neo4j_processor import neo4j_processor
        
        # Initialize processor
        processor = neo4j_processor()
        print("✅ neo4j_processor initialized successfully")
        
        # Test with sample data (adjust these IDs based on your actual data)
        test_cases = [
            ("https://modal.com/apps/ritesh3280-1/main", "https://modal.com/secrets/ritesh3280-1/main"),
        ]
        
        for start_id, end_id in test_cases:
            print(f"\n🔍 Testing path from '{start_id}' to '{end_id}'...")
            
            try:
                path_nodes = processor.find_shortest_path(start_id, end_id)
                
                if path_nodes:
                    print(f"✅ Path found with {len(path_nodes)} nodes:")
                    for i, node in enumerate(path_nodes[:5]):  # Show first 5 nodes
                        node_id = node.get('url') or node.get('id') or 'unknown'
                        print(f"   Step {i+1}: {node_id}")
                    if len(path_nodes) > 5:
                        print(f"   ... and {len(path_nodes) - 5} more nodes")
                else:
                    print("❌ No path found (this might be expected if nodes don't exist)")
                    
            except Exception as e:
                print(f"⚠️ Error during path finding: {str(e)}")
        
        # Close connection
        processor.close()
        print("\n✅ Connection closed successfully")
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("Make sure all dependencies are installed")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def test_navigation_tool():
    """Test the navigation_tool with updated neo4j_processor"""
    print("\n" + "=" * 60)
    print("Testing navigation_tool with updated neo4j_processor")
    print("=" * 60)
    
    try:
        from ai.navigation_tool import NavigationTool
        
        # Initialize navigation tool
        nav_tool = NavigationTool()
        print("✅ NavigationTool initialized successfully")
        
        # Test with a sample query
        test_query = "I want to buy a product"
        print(f"\n🧪 Testing query: '{test_query}'")
        
        # Extract intent
        intent = nav_tool.extract_intent(test_query)
        print(f"✅ Intent extracted: {intent.get('intent', 'unknown')}")
        
        # Test path finding (with mock data)
        start_url = "https://modal.com/apps/ritesh3280-1/main"
        end_url = "https://modal.com/secrets/ritesh3280-1/main"
        
        print(f"\n🗺️ Testing navigation from '{start_url}' to '{end_url}'...")
        path = nav_tool.get_navigation_path(start_url, end_url)
        
        if path:
            print(f"✅ Navigation path found with {len(path)} steps")
            for step in path[:3]:  # Show first 3 steps
                print(f"   {step['description']}")
        else:
            print("❌ No navigation path found (this might be expected if nodes don't exist)")
        
        # Close connections
        nav_tool.close()
        print("\n✅ NavigationTool closed successfully")
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("Make sure all dependencies are installed")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def main():
    """Run all tests"""
    print("\n🚀 Starting Neo4j Integration Tests\n")
    
    # Test neo4j_processor
    test_neo4j_processor()
    
    # Test navigation_tool
    test_navigation_tool()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
