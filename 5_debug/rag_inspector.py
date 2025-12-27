#!/usr/bin/env python3
import sys
import os
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init()

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../1_core')))

from embedding_store import EmbeddingStore

def print_header(text):
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{text.center(60)}")
    print(f"{'='*60}{Style.RESET_ALL}")

def main():
    store = EmbeddingStore()
    
    print_header("MENDYGO RAG TRANSPARENCY CLI")
    print(f"{Fore.YELLOW}Type your query to see exactly what Mendy retrieves.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Type 'exit' or 'quit' to stop.{Style.RESET_ALL}")

    while True:
        try:
            query = input(f"\n{Fore.GREEN}QUERY > {Style.RESET_ALL}").strip()
            if not query: continue
            if query.lower() in ['exit', 'quit']: break

            # 1. Keywords
            keywords = store._extract_keywords(query)
            print(f"\n{Fore.BLUE}[1] EXTRACTED KEYWORDS:{Style.RESET_ALL}")
            print(f" -> {', '.join(keywords) if keywords else 'None'}")

            # 2. Search Results
            print(f"\n{Fore.BLUE}[2] RETRIEVED CONTEXT (Top 5):{Style.RESET_ALL}")
            results = store.search(query, k=5)
            
            if not results:
                print(f"{Fore.RED} No results found for this query.{Style.RESET_ALL}")
                continue

            for i, res in enumerate(results, 1):
                m_type = res.get('match_type', 'unknown').upper()
                score = res.get('score', 0)
                color = Fore.GREEN if m_type == 'KEYWORD' else Fore.MAGENTA
                
                print(f"\n{color}{i}. [{m_type}] (Score: {score:.4f}){Style.RESET_ALL}")
                print(f"   Content: {res['content'][:200]}...")
                if 'metadata' in res:
                    meta = res['metadata']
                    if 'feeder' in meta: print(f"   Feeder: {meta['feeder']}")
                    if 'location' in meta: print(f"   Location: {meta['location']}")
                    if 'aliases' in meta: print(f"   Aliases: {meta['aliases']}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}Closing RAG Inspector. Goodbye!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
