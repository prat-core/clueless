#!/usr/bin/env python3
"""
Test script for WebCrawler fetch_page functionality.
Usage: python test_webscrape.py "google.com"
"""

import sys
import json
import argparse
from web_crawler import WebCrawler


def test_fetch_page(url):
    """Test the fetch_page and parse_page methods with a provided URL."""

    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'

    print(f"Testing fetch_page and parse_page with URL: {url}")

    # Initialize WebCrawler with dummy credentials (only testing fetch_page and parse_page)
    crawler = WebCrawler(
        neo4j_uri="bolt://localhost:7687",  # Dummy - not used in this test
        neo4j_auth=("neo4j", "password"),   # Dummy - not used in this test
        openai_api_key="dummy_key",         # Dummy - not used in this test
        base_url=url
    )

    try:
        # Test fetch_page method
        print("🌐 Fetching page content...")
        fetch_result = crawler.fetch_page(url)

        # Test parse_page method if we got HTML content
        parsed_data = None
        if fetch_result.get('html_content') and not fetch_result.get('error'):
            print("🔍 Parsing HTML content...")
            parsed_data = crawler.parse_page(fetch_result['html_content'], fetch_result['url'])

        # Prepare combined result
        result = {
            'fetch_data': fetch_result,
            'parsed_data': parsed_data
        }

        # Clean up the HTML content for JSON serialization (truncate if too long)
        if result['fetch_data'].get('html_content'):
            html_length = len(result['fetch_data']['html_content'])
            if html_length > 5000:  # Truncate long HTML content
                result['fetch_data']['html_content'] = result['fetch_data']['html_content'][:5000] + f"... [truncated, total length: {html_length}]"

        # Add test metadata
        result['test_metadata'] = {
            'test_url': url,
            'fetch_status': 'success' if result['fetch_data'].get('html_content') else 'failed',
            'parse_status': 'success' if parsed_data and not parsed_data.get('parse_error') else 'failed' if parsed_data else 'not_attempted'
        }

        # Save results to JSON file
        with open('result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"✅ Test completed successfully!")
        print(f"📊 Results saved to result.json")
        print(f"🌐 Final URL: {result['fetch_data'].get('url', 'N/A')}")
        print(f"⏱️  Response time: {result['fetch_data'].get('response_time_ms', 0):.2f}ms")
        print(f"📄 HTML content length: {len(result['fetch_data'].get('html_content', '')) if result['fetch_data'].get('html_content') else 0} characters")

        if parsed_data:
            print(f"📝 Page title: {parsed_data.get('title', 'N/A')}")
            print(f"🔗 Links found: {parsed_data.get('link_count', 0)}")
            print(f"🖼️  Images found: {parsed_data.get('image_count', 0)}")
            print(f"📱 Clickable elements: {len(parsed_data.get('clickable_elements', []))}")
            print(f"📏 Content length: {parsed_data.get('content_length', 0)} characters")

        if result['fetch_data'].get('error'):
            print(f"⚠️  Fetch Error: {result['fetch_data']['error']}")

        if parsed_data and parsed_data.get('parse_error'):
            print(f"⚠️  Parse Error: {parsed_data['parse_error']}")

        return result

    except Exception as e:
        error_result = {
            'fetch_data': {
                'url': url,
                'html_content': None,
                'error': f'Test failed with exception: {str(e)}'
            },
            'parsed_data': None,
            'test_metadata': {
                'test_url': url,
                'fetch_status': 'error',
                'parse_status': 'not_attempted'
            }
        }

        with open('result.json', 'w', encoding='utf-8') as f:
            json.dump(error_result, f, indent=2, ensure_ascii=False)

        print(f"❌ Test failed with error: {e}")
        return error_result

    finally:
        # Cleanup selenium driver
        if hasattr(crawler, 'selenium_driver') and crawler.selenium_driver:
            try:
                crawler.selenium_driver.quit()
                print("🧹 Selenium driver cleaned up")
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description='Test WebCrawler fetch_page and parse_page functionality')
    parser.add_argument('url', help='URL to test (e.g., google.com)')

    args = parser.parse_args()

    print("🚀 Starting WebCrawler fetch_page and parse_page test")
    print("=" * 50)

    result = test_fetch_page(args.url)

    print("=" * 50)
    print("🏁 Test completed")


if __name__ == "__main__":
    main()