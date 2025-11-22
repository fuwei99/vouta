import base64
import re
import json
import time
    if hasattr(gemini_response_candidate, 'text') and gemini_response_candidate.text is not None:
        candidate_part_text = str(gemini_response_candidate.text)

    gemini_candidate_content = None
    if hasattr(gemini_response_candidate, 'content'):
        gemini_candidate_content = gemini_response_candidate.content

    if gemini_candidate_content and hasattr(gemini_candidate_content, 'parts') and gemini_candidate_content.parts:
        for part_item in gemini_candidate_content.parts:
            if hasattr(part_item, 'function_call') and part_item.function_call is not None: # Kilo Code: Added 'is not None' check
                continue
            
            part_text = ""
            if hasattr(part_item, 'text') and part_item.text is not None:
                part_text = str(part_item.text)
            
            # Check for image parts
            elif hasattr(part_item, 'inline_data') and part_item.inline_data is not None:
                # Handle image data in response
                inline_data = part_item.inline_data
                if hasattr(inline_data, 'data') and hasattr(inline_data, 'mime_type'):
                    image_bytes = inline_data.data
                    mime_type = inline_data.mime_type
                    # Convert image to markdown format
                    part_text = _convert_image_to_markdown(image_bytes, mime_type)
            
            # Check for blob/file reference (for images stored in blob)
            elif hasattr(part_item, 'file_data') and part_item.file_data is not None:
                # Handle file reference (typically for images)
                file_data = part_item.file_data
                if hasattr(file_data, 'file_uri'):
                    # Create a markdown link to the file
                    file_uri = file_data.file_uri
                    mime_type = getattr(file_data, 'mime_type', 'image/png')
                    # For file URIs, we can't embed directly, so we'll create a link
                    part_text = f"![Image]({file_uri})"
                    print(f"Image file reference found: {file_uri}")
            
            part_is_thought = hasattr(part_item, 'thought') and part_item.thought is True

            if part_is_thought:
                reasoning_text_parts.append(part_text)
            elif part_text: # Only add if it's not a function_call and has text or converted image
                normal_text_parts.append(part_text)
    elif candidate_part_text:
        normal_text_parts.append(candidate_part_text)
    elif gemini_candidate_content and hasattr(gemini_candidate_content, 'text') and gemini_candidate_content.text is not None:
        normal_text_parts.append(str(gemini_candidate_content.text))
    elif hasattr(gemini_response_candidate, 'text') and gemini_response_candidate.text is not None and not gemini_candidate_content: # Should be caught by candidate_part_text
        normal_text_parts.append(str(gemini_response_candidate.text))

    return "".join(reasoning_text_parts), "".join(normal_text_parts)

# This function will be the core for converting a full Gemini response.
# It will be called by the non-streaming path and the fake-streaming path.
def process_gemini_response_to_openai_dict(gemini_response_obj: Any, request_model_str: str) -> Dict[str, Any]:
    is_encrypt_full = request_model_str.endswith("-encrypt-full")
    choices = []
    response_timestamp = int(time.time())
    base_id = f"chatcmpl-{response_timestamp}-{random.randint(1000,9999)}"

    if hasattr(gemini_response_obj, 'candidates') and gemini_response_obj.candidates:
        for i, candidate in enumerate(gemini_response_obj.candidates):
            message_payload = {"role": "assistant"}
            
            raw_finish_reason = getattr(candidate, 'finish_reason', None)
            openai_finish_reason = "stop" # Default
            if raw_finish_reason:
                if hasattr(raw_finish_reason, 'name'): raw_finish_reason_str = raw_finish_reason.name.upper()
                else: raw_finish_reason_str = str(raw_finish_reason).upper()

                if raw_finish_reason_str == "STOP": openai_finish_reason = "stop"
                elif raw_finish_reason_str == "MAX_TOKENS": openai_finish_reason = "length"
                elif raw_finish_reason_str == "SAFETY": openai_finish_reason = "content_filter"
                elif raw_finish_reason_str in ["TOOL_CODE", "FUNCTION_CALL"]: openai_finish_reason = "tool_calls"
                # Other reasons like RECITATION, OTHER map to "stop" or a more specific OpenAI reason if available.
            
            function_call_detected = False
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, 'function_call') and part.function_call is not None: # Kilo Code: Added 'is not None' check
                        fc = part.function_call
                        tool_call_id = f"call_{base_id}_{i}_{fc.name.replace(' ', '_')}_{int(time.time()*10000 + random.randint(0,9999))}"
                        
                        if "tool_calls" not in message_payload:
                            message_payload["tool_calls"] = []
                        
                        message_payload["tool_calls"].append({
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": fc.name,
                                "arguments": json.dumps(fc.args or {})
                            }
                        })
                        message_payload["content"] = None 
                        openai_finish_reason = "tool_calls" # Override if a tool call is made
                        function_call_detected = True
            
            if not function_call_detected:
                reasoning_str, normal_content_str = parse_gemini_response_for_reasoning_and_content(candidate)
                if is_encrypt_full:
                    reasoning_str = deobfuscate_text(reasoning_str)
                    normal_content_str = deobfuscate_text(normal_content_str)
                
                if app_config.SAFETY_SCORE and hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    safety_html = _create_safety_ratings_html(candidate.safety_ratings)
                    if reasoning_str:
                        reasoning_str += safety_html
                    else:
                        normal_content_str += safety_html
                
                message_payload["content"] = normal_content_str
                if reasoning_str:
                    message_payload['reasoning_content'] = reasoning_str
            
            choice_item = {"index": i, "message": message_payload, "finish_reason": openai_finish_reason}
            if hasattr(candidate, 'logprobs') and candidate.logprobs is not None:
                 choice_item["logprobs"] = candidate.logprobs
            choices.append(choice_item)
            
    elif hasattr(gemini_response_obj, 'text') and gemini_response_obj.text is not None:
         content_str = deobfuscate_text(gemini_response_obj.text) if is_encrypt_full else (gemini_response_obj.text or "")
         choices.append({"index": 0, "message": {"role": "assistant", "content": content_str}, "finish_reason": "stop"})
    else: 
         choices.append({"index": 0, "message": {"role": "assistant", "content": None}, "finish_reason": "stop"})

    usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    if hasattr(gemini_response_obj, 'usage_metadata'):
        um = gemini_response_obj.usage_metadata
        if hasattr(um, 'prompt_token_count'): usage_data['prompt_tokens'] = um.prompt_token_count
        # Gemini SDK might use candidates_token_count or total_token_count for completion.
        # Prioritize candidates_token_count if available.
        if hasattr(um, 'candidates_token_count'):
            usage_data['completion_tokens'] = um.candidates_token_count
            if hasattr(um, 'total_token_count'): # Ensure total is sum if both available
                 usage_data['total_tokens'] = um.total_token_count
            else: # Estimate total if only prompt and completion are available
                 usage_data['total_tokens'] = usage_data['prompt_tokens'] + usage_data['completion_tokens']
        elif hasattr(um, 'total_token_count'): # Fallback if only total is available
             usage_data['total_tokens'] = um.total_token_count
             if usage_data['prompt_tokens'] > 0 and usage_data['total_tokens'] > usage_data['prompt_tokens']:
                 usage_data['completion_tokens'] = usage_data['total_tokens'] - usage_data['prompt_tokens']
        else: # If only prompt_token_count is available, completion and total might remain 0 or be estimated differently
            usage_data['total_tokens'] = usage_data['prompt_tokens'] # Simplistic fallback

    return {
        "id": base_id, "object": "chat.completion", "created": response_timestamp,
        "model": request_model_str, "choices": choices,
        "usage": usage_data
    }

# Keep convert_to_openai_format as a wrapper for now if other parts of the code call it directly.
def convert_to_openai_format(gemini_response: Any, model: str) -> Dict[str, Any]:
    return process_gemini_response_to_openai_dict(gemini_response, model)


def convert_chunk_to_openai(chunk: Any, model_name: str, response_id: str, candidate_index: int = 0) -> str:
    is_encrypt_full = model_name.endswith("-encrypt-full")
    delta_payload = {}
    openai_finish_reason = None

    if hasattr(chunk, 'candidates') and chunk.candidates:
        candidate = chunk.candidates[0] # Process first candidate for streaming
        raw_gemini_finish_reason = getattr(candidate, 'finish_reason', None)
        if raw_gemini_finish_reason:
            if hasattr(raw_gemini_finish_reason, 'name'): raw_gemini_finish_reason_str = raw_gemini_finish_reason.name.upper()
            else: raw_gemini_finish_reason_str = str(raw_gemini_finish_reason).upper()

            if raw_gemini_finish_reason_str == "STOP": openai_finish_reason = "stop"
            elif raw_gemini_finish_reason_str == "MAX_TOKENS": openai_finish_reason = "length"
            elif raw_gemini_finish_reason_str == "SAFETY": openai_finish_reason = "content_filter"
            elif raw_gemini_finish_reason_str in ["TOOL_CODE", "FUNCTION_CALL"]: openai_finish_reason = "tool_calls"
            # Not setting a default here; None means intermediate chunk unless reason is terminal.

        function_call_detected_in_chunk = False
        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call is not None: # Kilo Code: Added 'is not None' check
                    fc = part.function_call
                    tool_call_id = f"call_{response_id}_{candidate_index}_{fc.name.replace(' ', '_')}_{int(time.time()*10000 + random.randint(0,9999))}"
                    
                    current_tool_call_delta = {
                        "index": 0, 
                        "id": tool_call_id,
                        "type": "function",
                        "function": {"name": fc.name}
                    }
                    if fc.args is not None: # Gemini usually sends full args.
                        current_tool_call_delta["function"]["arguments"] = json.dumps(fc.args)
                    else: # If args could be streamed (rare for Gemini FunctionCall part)
                        current_tool_call_delta["function"]["arguments"] = "" 

                    if "tool_calls" not in delta_payload:
                        delta_payload["tool_calls"] = []
                    delta_payload["tool_calls"].append(current_tool_call_delta)
                    
                    delta_payload["content"] = None 
                    function_call_detected_in_chunk = True
                    # If this chunk also has the finish_reason for tool_calls, it will be set.
                    break 

        if not function_call_detected_in_chunk:
            reasoning_text, normal_text = parse_gemini_response_for_reasoning_and_content(candidate)
            if is_encrypt_full:
                reasoning_text = deobfuscate_text(reasoning_text)
                normal_text = deobfuscate_text(normal_text)

            if app_config.SAFETY_SCORE and hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                safety_html = _create_safety_ratings_html(candidate.safety_ratings)
                if reasoning_text:
                    reasoning_text += safety_html
                else:
                    normal_text += safety_html

            if reasoning_text: delta_payload['reasoning_content'] = reasoning_text
            if normal_text: # Only add content if it's non-empty
                delta_payload['content'] = normal_text
            elif not reasoning_text and not delta_payload.get("tool_calls") and openai_finish_reason is None:
                # If no other content and not a terminal chunk, send empty content string
                delta_payload['content'] = ""
    
    if not delta_payload and openai_finish_reason is None:
        # This case ensures that even if a chunk is completely empty (e.g. keep-alive or error scenario not caught above)
        # and it's not a terminal chunk, we still send a delta with empty content.
        delta_payload['content'] = ""

    chunk_data = {
        "id": response_id, "object": "chat.completion.chunk", "created": int(time.time()), "model": model_name,
        "choices": [{"index": candidate_index, "delta": delta_payload, "finish_reason": openai_finish_reason}]
    }
    # Logprobs are typically not in streaming deltas for OpenAI.
    return f"data: {json.dumps(chunk_data)}\n\n"

def create_final_chunk(model: str, response_id: str, candidate_count: int = 1) -> str:
    # This function might need adjustment if the finish reason isn't always "stop"
    # For now, it's kept as is, but tool_calls might require a different final chunk structure
    # if not handled by the last delta from convert_chunk_to_openai.
    # However, OpenAI expects the last content/tool_call delta to carry the finish_reason.
    # This function is more of a safety net or for specific scenarios.
    choices = [{"index": i, "delta": {}, "finish_reason": "stop"} for i in range(candidate_count)]
    final_chunk_data = {"id": response_id, "object": "chat.completion.chunk", "created": int(time.time()), "model": model, "choices": choices}
    return f"data: {json.dumps(final_chunk_data)}\n\n"