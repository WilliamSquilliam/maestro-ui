"""Maestro — Multi-Agent Orchestrator entry point.

Usage:
    python main.py                    # Start the CLI REPL
    python main.py --ui               # Start the web UI server
    python main.py --keep-alive       # Keep Docker containers alive after exit
    python main.py --anthropic        # Use Anthropic API directly
"""
import argparse
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Maestro Multi-Agent Orchestrator")
    parser.add_argument(
        "--keep-alive",
        action="store_true",
        help="Keep Docker containers alive after the session ends.",
    )
    parser.add_argument(
        "--anthropic",
        action="store_true",
        help="Use Anthropic API directly instead of the default provider.",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Start the web UI server instead of the CLI REPL.",
    )

    args = parser.parse_args()

    if args.ui:
        # Start the web UI API server
        import uvicorn
        from api_server import api_app

        logger.info("Starting Maestro UI server on http://0.0.0.0:8080")
        print("\n" + "=" * 60)
        print("Maestro UI Server")
        print("Open http://localhost:8080 in your browser")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        try:
            uvicorn.run(api_app, host="0.0.0.0", port=8080, log_level="info")
        except KeyboardInterrupt:
            print("\nShutting down UI server...")
    else:
        # CLI REPL mode
        try:
            from langchain_core.messages import HumanMessage
            from graph import app as langgraph_app
        except ImportError as e:
            logger.error(f"Failed to import graph dependencies: {e}")
            print(
                "Error: Required packages not installed. "
                "Run: pip install -r requirements.txt"
            )
            return

        config = {"configurable": {"thread_id": "1"}}

        print("\n" + "=" * 60)
        print("Maestro — Multi-Agent Orchestrator (CLI)")
        print("Type your message to begin. Press Ctrl+C to exit.")
        print("=" * 60)

        while True:
            try:
                user_input = input("\nUser (Orchestrator): ")
            except (KeyboardInterrupt, EOFError):
                print("\nExiting Maestro...")
                break

            if not user_input.strip():
                continue

            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "execution_plan": "",
                "next_actor": "",
                "consecutive_worker_loops": 0,
            }

            try:
                for event in langgraph_app.stream(
                    initial_state, config=config, stream_mode="updates"
                ):
                    for node_name, node_state in event.items():
                        if not isinstance(node_state, dict):
                            continue
                        print(f"\n--- [{node_name}] ---")
                        if (
                            "execution_plan" in node_state
                            and node_state["execution_plan"]
                        ):
                            print(f"Plan: {node_state['execution_plan']}")
                        if "messages" in node_state and node_state["messages"]:
                            for msg in node_state["messages"]:
                                content = (
                                    msg.content
                                    if hasattr(msg, "content")
                                    else str(msg)
                                )
                                print(content)
                        if "next_actor" in node_state:
                            print(f"Next: {node_state['next_actor']}")
            except Exception as e:
                logger.error(f"Graph execution error: {e}")
                print(f"\nError: {e}")


if __name__ == "__main__":
    main()
