import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from llama_cpp import Llama
import pymysql


class ChatModel:
    """
    Chat processor using Llama model for text processing and summarization.
    Supports conversation history and various input types.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 2048,
        n_batch: int = 512,
        max_tokens_limit: int = 1500,
        verbose: bool = False
    ):
        """
        Initialize the ChatModel.
        
        Args:
            model_path: Path to the model file. If None, uses default project path.
            n_ctx: Context window size.
            n_batch: Batch size for processing.
            max_tokens_limit: Maximum tokens limit.
            verbose: Whether to print verbose output.
        """
        # Set default model path if not provided
        if model_path is None:
            # Try to find model in project directory
            project_root = Path(__file__).parent.parent.parent
            default_model = project_root / "model" / "llama-3.2-1b-instruct-q8_0.gguf"
            if default_model.exists():
                model_path = str(default_model)
            else:
                # Fallback to original path
                model_path = "/Users/katerynahunko/presents/models/llama-3.2-1b-instruct-q8_0.gguf"
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_batch = n_batch
        self.max_tokens_limit = max_tokens_limit
        self.verbose = verbose
        
        if self.verbose:
            print(f"Loading model from: {model_path}")
        
        try:
            self.llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_batch=n_batch,
                verbose=verbose,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}") from e
        
        # Conversation history
        self.conversation_history: List[Dict[str, str]] = []
        
        if self.verbose:
            print("Model loaded successfully!")

    def generate_response(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
        echo: bool = False,
        stop: Optional[List[str]] = None,
    ) -> str:
        """
        Generate a response from the model.
        
        Args:
            prompt: Input prompt text.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature (0.0 to 1.0).
            top_p: Top-p sampling parameter.
            top_k: Top-k sampling parameter.
            repeat_penalty: Penalty for repeating tokens.
            echo: Whether to echo the prompt in output.
            stop: List of stop sequences.
            
        Returns:
            Generated text response.
        """
        if stop is None:
            stop = ["<|eot_id|>", "<|end_header_id|>", "\n\n\n"]
        
        # Estimate token count and adjust max_tokens if needed
        estimated_tokens = len(prompt) // 4  # Rough estimate
        if estimated_tokens + max_tokens > self.max_tokens_limit:
            max_tokens = max(20, self.max_tokens_limit - estimated_tokens)
        
        try:
            output = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repeat_penalty=repeat_penalty,
                echo=echo,
                stop=stop,
            )
            
            response = output["choices"][0]["text"].strip()
            
            # Clean up response
            response = self._clean_response(response)
            
            return response
            
        except Exception as e:
            if self.verbose:
                print(f"Error generating response: {e}")
            return f"Error: {str(e)}"

    def _clean_response(self, response: str) -> str:
        """Clean up the response text."""
        # Remove common artifacts
        response = response.replace("<|eot_id|>", "")
        response = response.replace("<|end_header_id|>", "")
        response = response.replace("<|start_header_id|>", "")
        response = response.replace("assistant", "")
        response = response.replace("user", "")
        
        # Remove extra whitespace
        response = " ".join(response.split())
        
        return response.strip()

    def generate_prompt(
        self,
        user_input: str,
        task_type: str = "general",
        include_history: bool = True
    ) -> str:
        """
        Generate a formatted prompt for the model.
        
        Args:
            user_input: User's input text.
            task_type: Type of task ('general', 'summarize', 'analyze').
            include_history: Whether to include conversation history.
            
        Returns:
            Formatted prompt string.
        """
        # System prompt based on task type
        if task_type == "summarize":
            system_prompt = """You are a helpful assistant that summarizes text concisely.
Extract key information including:
- Main points and topics
- Important facts and figures
- Pricing information (if present) in format: {"package": "NAME", "price": "PRICE"}
- Key dates, names, and locations
- Action items or recommendations

Keep the summary concise and focused on essential information."""
        elif task_type == "analyze":
            system_prompt = """You are an analytical assistant that analyzes text and extracts structured information.
Provide analysis including:
- Key themes and topics
- Important details and specifications
- Relationships and connections
- Insights and conclusions"""
        else:
            system_prompt = """You are a helpful, knowledgeable assistant.
Provide clear, concise, and accurate responses to user queries."""
        
        # Build conversation history if enabled
        history_text = ""
        if include_history and self.conversation_history:
            history_text = "\n\nPrevious conversation:\n"
            for msg in self.conversation_history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_text += f"{role}: {content}\n"
        
        # Format prompt for Llama 3.2 instruct format
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>
{history_text}{user_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""
        
        return prompt

    def chat(
        self,
        user_input: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        task_type: str = "general",
        save_to_history: bool = True
    ) -> str:
        """
        Process user input and return chat response.
        
        Args:
            user_input: User's input message.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            task_type: Type of task ('general', 'summarize', 'analyze').
            save_to_history: Whether to save to conversation history.
            
        Returns:
            Model's response text.
        """
        if not user_input or not user_input.strip():
            return "Please provide a valid input."
        
        # Generate prompt
        prompt = self.generate_prompt(user_input, task_type=task_type)
        
        # Generate response
        response = self.generate_response(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        # Save to history if enabled
        if save_to_history:
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })
        
        return response

    def summarize(
        self,
        text: str,
        max_tokens: int = 200,
        temperature: float = 0.5
    ) -> str:
        """
        Summarize a text block.
        
        Args:
            text: Text to summarize.
            max_tokens: Maximum tokens for summary.
            temperature: Sampling temperature.
            
        Returns:
            Summary text.
        """
        return self.chat(
            user_input=f"Summarize the following text:\n\n{text}",
            max_tokens=max_tokens,
            temperature=temperature,
            task_type="summarize",
            save_to_history=False
        )

    def analyze(
        self,
        text: str,
        max_tokens: int = 300,
        temperature: float = 0.6
    ) -> str:
        """
        Analyze a text block.
        
        Args:
            text: Text to analyze.
            max_tokens: Maximum tokens for analysis.
            temperature: Sampling temperature.
            
        Returns:
            Analysis text.
        """
        return self.chat(
            user_input=f"Analyze the following text:\n\n{text}",
            max_tokens=max_tokens,
            temperature=temperature,
            task_type="analyze",
            save_to_history=False
        )

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        if self.verbose:
            print("Conversation history cleared.")

    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self.conversation_history.copy()

    def process_json_input(
        self,
        input_data: Dict[str, Any],
        task: str = "summarize"
    ) -> Dict[str, Any]:
        """
        Process structured JSON input.
        
        Args:
            input_data: Dictionary with input data.
            task: Task type ('summarize', 'analyze', 'general').
            
        Returns:
            Dictionary with processed results.
        """
        results = {}
        
        # Process text fields
        if "text" in input_data:
            if task == "summarize":
                results["summary"] = self.summarize(input_data["text"])
            elif task == "analyze":
                results["analysis"] = self.analyze(input_data["text"])
            else:
                results["response"] = self.chat(input_data["text"], task_type=task)
        
        # Process multiple texts
        if "texts" in input_data and isinstance(input_data["texts"], list):
            summaries = []
            for text in input_data["texts"]:
                if task == "summarize":
                    summaries.append(self.summarize(text))
                else:
                    summaries.append(self.chat(text, task_type=task))
            results["summaries"] = summaries
        
        return results


# Example usage and testing
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Chat Processor - Llama Model')
    parser.add_argument('input', nargs='*', help='Input text to process')
    parser.add_argument('--file', type=str, help='Read input from file')
    parser.add_argument('--task', type=str, default='general', choices=['general', 'summarize', 'analyze'], help='Task type')
    parser.add_argument('--max-tokens', type=int, default=200, help='Maximum tokens to generate')
    parser.add_argument('--json', action='store_true', help='JSON input mode')
    parser.add_argument('--quiet', action='store_true', help='Quiet mode (no verbose output)')
    
    args = parser.parse_args()
    
    if not args.quiet:
        print("=" * 60)
        print("Chat Processor - Llama Model")
        print("=" * 60)
    
    try:
        # Initialize the chat model
        if not args.quiet:
            print("\nInitializing chat model...")
        chat = ChatModel(verbose=not args.quiet)
        
        # File input mode
        if args.file:
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    input_text = f.read()
                
                if args.task == 'summarize':
                    response = chat.summarize(input_text, max_tokens=args.max_tokens)
                elif args.task == 'analyze':
                    response = chat.analyze(input_text, max_tokens=args.max_tokens)
                else:
                    response = chat.chat(input_text, max_tokens=args.max_tokens, task_type=args.task)
                
                print(response)
                
            except FileNotFoundError:
                print(f"Error: File not found: {args.file}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        
        # JSON input mode
        elif args.json:
            import json as json_module
            if len(sys.argv) >= 3:
                try:
                    input_json = json_module.loads(" ".join(sys.argv[2:]))
                    result = chat.process_json_input(input_json, task=args.task)
                    print(json_module.dumps(result, indent=2))
                except json_module.JSONDecodeError:
                    print("Error: Invalid JSON input", file=sys.stderr)
                    sys.exit(1)
            else:
                print("Usage: python processor.py --json '{\"text\": \"your text\"}'", file=sys.stderr)
                sys.exit(1)
        
        # Interactive mode if no arguments
        elif len(sys.argv) == 1:
            print("\n" + "=" * 60)
            print("Interactive Chat Mode")
            print("Commands:")
            print("  - Type your message and press Enter")
            print("  - 'summarize <text>' - Summarize text")
            print("  - 'analyze <text>' - Analyze text")
            print("  - 'clear' - Clear conversation history")
            print("  - 'history' - Show conversation history")
            print("  - 'quit' or 'exit' - Exit")
            print("=" * 60 + "\n")
            
            while True:
                try:
                    user_input = input("\nYou: ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("\nGoodbye!")
                        break
                    
                    if user_input.lower() == 'clear':
                        chat.clear_history()
                        print("Conversation history cleared.")
                        continue
                    
                    if user_input.lower() == 'history':
                        history = chat.get_history()
                        if history:
                            print("\nConversation History:")
                            for i, msg in enumerate(history, 1):
                                print(f"  {i}. {msg['role']}: {msg['content'][:100]}...")
                        else:
                            print("No conversation history.")
                        continue
                    
                    if user_input.lower().startswith('summarize '):
                        text = user_input[10:].strip()
                        response = chat.summarize(text)
                    elif user_input.lower().startswith('analyze '):
                        text = user_input[8:].strip()
                        response = chat.analyze(text)
                    else:
                        response = chat.chat(user_input)
                    
                    print(f"\nAssistant: {response}")
                    
                except KeyboardInterrupt:
                    print("\n\nGoodbye!")
                    break
                except Exception as e:
                    print(f"\nError: {e}")
        
        # Single input mode (text passed as arguments)
        elif args.input:
            input_text = " ".join(args.input)
            if not args.quiet:
                print(f"\nInput: {input_text[:100]}...")
                print("\nProcessing...")
            
            if args.task == 'summarize':
                response = chat.summarize(input_text, max_tokens=args.max_tokens)
            elif args.task == 'analyze':
                response = chat.analyze(input_text, max_tokens=args.max_tokens)
            else:
                response = chat.chat(input_text, max_tokens=args.max_tokens, task_type=args.task)
            
            if not args.quiet:
                print(f"\nResponse: {response}")
            else:
                print(response)
    
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease ensure the model file exists at the specified path.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
