import os
import tempfile
import requests
import json
import time
from pytube import YouTube
import yt_dlp
from pydub import AudioSegment
import re
import uuid
import argparse
import logging # Added logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HF_API_TOKEN = "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"

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def download_youtube_audio(youtube_url, output_dir=None):
    # ... (previous code)
    if output_dir is None:
        # Use a specific temporary directory for this app if desired
        output_dir = tempfile.mkdtemp(prefix="coursegen_audio_")
        logging.info(f"Created temporary directory for audio: {output_dir}")

    # ... (rest of the function)
    try:
        # Use video title (optional: replace with UUID if anonymity is needed)
        yt = YouTube(youtube_url)
        base_filename = sanitize_filename(yt.title)
    except Exception as e:
        logging.warning(f"Could not get YouTube title: {e}")
        base_filename = str(uuid.uuid4())

    output_template = os.path.join(output_dir, f"{base_filename}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logging.info(f"Starting audio download for {youtube_url}")
            info = ydl.extract_info(youtube_url, download=True)

            base_path_without_ext = os.path.splitext(output_template)[0]
            downloaded_files = [f for f in os.listdir(output_dir)
                                if f.startswith(os.path.basename(base_path_without_ext))]

            if not downloaded_files:
                raise FileNotFoundError(f"No audio file found starting with {base_path_without_ext}")

            audio_path = os.path.join(output_dir, os.path.splitext(downloaded_files[0])[0] + '.mp3')

            if not os.path.exists(audio_path):
                potential_original = os.path.join(output_dir, downloaded_files[0])
                if os.path.exists(potential_original):
                    logging.warning(f"MP3 not found. Attempting manual conversion from {potential_original}.")
                    try:
                        sound = AudioSegment.from_file(potential_original)
                        sound.export(audio_path, format="mp3")
                        logging.info(f"Converted manually to {audio_path}")
                    except Exception as conversion_e:
                        logging.error(f"Manual conversion failed: {conversion_e}")
                        raise FileNotFoundError(f"Conversion failed. No MP3 file found at {audio_path}")
                else:
                    raise FileNotFoundError(f"No valid file found at expected paths.")
        
        logging.info(f"Audio saved to: {audio_path}")
        return audio_path

    except Exception as e:
        logging.error(f"Failed to download or convert audio: {e}", exc_info=True)
        raise


def split_audio_into_chunks(audio_path, chunk_length_ms=29000, output_dir=None): # Increased chunk length
    """
    Splits audio into chunks. Increased default chunk length for potentially better transcription context.
    """
    if not os.path.exists(audio_path):
        logging.error(f"Audio file not found for splitting: {audio_path}")
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if output_dir is None:
        output_dir = os.path.dirname(audio_path)

    logging.info(f"Loading audio file: {audio_path}")
    try:
        # Explicitly state format if known, helps with potential issues
        audio = AudioSegment.from_file(audio_path, format="mp3")
    except Exception as e:
        logging.error(f"Error loading audio file {audio_path}: {e}", exc_info=True)
        raise

    # Generate a base name for chunks using unique identifier
    # Use the audio filename base for easier association
    audio_filename_base = os.path.splitext(os.path.basename(audio_path))[0]
    base_name = f"{audio_filename_base}_chunk"

    chunks = []
    logging.info(f"Splitting audio into chunks of {chunk_length_ms}ms...")
    for i, chunk_start in enumerate(range(0, len(audio), chunk_length_ms)):
        chunk_end = chunk_start + chunk_length_ms # Don't use min(), just export the segment
        chunk = audio[chunk_start:chunk_end]

        # Ensure chunk has minimum length to avoid issues with very short final chunks
        if len(chunk) < 500: # Skip chunks less than 0.5 seconds
             logging.warning(f"Skipping very short chunk {i} (length: {len(chunk)}ms)")
             continue


        chunk_path = os.path.join(output_dir, f"{base_name}_{i}.mp3")

        try:
            logging.info(f"Exporting chunk {i}: {chunk_path}")
            chunk.export(chunk_path, format="mp3")
            chunks.append(chunk_path)
        except Exception as export_e:
            logging.error(f"Error exporting chunk {i} to {chunk_path}: {export_e}", exc_info=True)
            # Decide whether to stop or continue; continuing might lead to incomplete transcription
            # For now, we'll log and continue, but the calling function should be aware
            chunks.append(None) # Indicate a failed chunk


    logging.info(f"Split audio into {len([c for c in chunks if c is not None])} valid chunks (out of {len(chunks)} attempts)")
    return chunks


# --- Transcription function using Hugging Face API ---
def transcribe_audio_chunk_hf_api(audio_path, hf_token):
    """
    Transcribes audio file using Whisper model via Hugging Face API.
    Handles retries on 503 errors.
    """
    if not hf_token:
        logging.error("Hugging Face API token is missing.")
        return "[Transcription Error: Missing API Token]"

    if not audio_path or not os.path.exists(audio_path):
        logging.error(f"Audio chunk file not found or invalid: {audio_path}")
        return "[Transcription Error: Invalid Audio File Path]"

    logging.info(f"Transcribing audio chunk: {os.path.basename(audio_path)}")
    # Using openai/whisper-large-v3 - check Hugging Face for latest/best models
    API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
    headers = {"Authorization": f"Bearer {hf_token}"}

    try:
        with open(audio_path, "rb") as f:
            data = f.read()
        if not data:
             logging.warning(f"Audio chunk file is empty: {audio_path}")
             return "" # Return empty string for empty file
    except Exception as e:
        logging.error(f"Error reading audio file {audio_path}: {e}", exc_info=True)
        return f"[Transcription Error: Cannot read audio file {os.path.basename(audio_path)}]"

    max_retries = 5
    retry_delay = 15 # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            # Consider adding 'chunk_length_s' if supported by the model/API for better accuracy
            response = requests.post(
                API_URL,
                headers=headers,
                data=data,
                # params={"return_timestamps": "word"} # Example: get word timestamps if needed
                timeout=60 # Add a timeout
            )

            logging.debug(f"HF API response status: {response.status_code} for {os.path.basename(audio_path)}")

            if response.status_code == 200:
                result = response.json()
                transcription = result.get("text", "").strip()
                logging.info(f"Successfully transcribed chunk: {os.path.basename(audio_path)}")
                return transcription
            elif response.status_code == 503: # Model loading or server busy
                wait_time = int(response.headers.get("Retry-After", retry_delay))
                logging.warning(f"Server busy (503). Retrying attempt {attempt + 1}/{max_retries} after {wait_time} seconds for {os.path.basename(audio_path)}...")
                time.sleep(wait_time)
                retry_delay *= 1.5 # Exponential backoff (optional)
            elif response.status_code == 400: # Bad request (e.g., audio format issue)
                 logging.error(f"HF API Bad Request (400) for {os.path.basename(audio_path)}. Response: {response.text}")
                 return f"[Transcription Error: Bad Request - Check Audio Format/API Params for {os.path.basename(audio_path)}]"
            elif response.status_code == 429: # Rate limit
                 logging.error(f"HF API Rate Limit Hit (429) for {os.path.basename(audio_path)}. Response: {response.text}")
                 # Consider waiting longer or stopping
                 wait_time = int(response.headers.get("Retry-After", 60))
                 time.sleep(wait_time)
            else:
                # Handle other unexpected errors
                logging.error(f"HF API Error {response.status_code} for {os.path.basename(audio_path)}. Response: {response.text}")
                # Don't retry on definitive errors like 401, 403, 404 etc. Break loop.
                return f"[Transcription Error: API failed ({response.status_code}) for {os.path.basename(audio_path)}]"

        except requests.exceptions.RequestException as e:
            logging.error(f"Network/Request error during transcription for {os.path.basename(audio_path)} (attempt {attempt + 1}): {e}", exc_info=True)
            if attempt >= max_retries - 1:
                 return f"[Transcription Error: Network/Request failed after retries for {os.path.basename(audio_path)}]"
            time.sleep(retry_delay) # Wait before retrying network errors

    # If loop finishes without success
    logging.error(f"Transcription failed for chunk {os.path.basename(audio_path)} after {max_retries} attempts.")
    return f"[Transcription Error: Failed after retries for {os.path.basename(audio_path)}]"


# --- Full transcription function ---
def transcribe_full_audio(audio_path, hf_token):
    """
    Transcribes full audio by splitting, processing chunks, and combining results.
    """
    full_transcription = ""
    chunks = []
    temp_dir = os.path.dirname(audio_path) # Use audio file's directory for chunks

    try:
        # Split audio into chunks
        chunks = split_audio_into_chunks(audio_path, output_dir=temp_dir)

        # Process each chunk
        transcriptions = []
        for i, chunk_path in enumerate(chunks):
            if chunk_path is None:
                logging.warning(f"Skipping transcription for failed chunk export (index {i})")
                transcriptions.append("[Transcription Error: Audio chunk export failed]")
                continue
            try:
                # Use the function that handles retries
                chunk_transcription = transcribe_audio_chunk_hf_api(chunk_path, hf_token)
                transcriptions.append(chunk_transcription)
            except Exception as e:
                # Log error but continue with other chunks
                logging.error(f"Error transcribing chunk {os.path.basename(chunk_path)}: {e}", exc_info=True)
                transcriptions.append(f"[Transcription error for segment {i}]")
            finally:
                 # Clean up individual chunk file immediately after processing
                 if os.path.exists(chunk_path):
                     try:
                         os.remove(chunk_path)
                         logging.debug(f"Removed chunk file: {chunk_path}")
                     except OSError as remove_e:
                         logging.warning(f"Could not remove chunk file {chunk_path}: {remove_e}")


        # Combine transcriptions
        full_transcription = " ".join(filter(None, transcriptions)).strip() # Join non-empty results
        logging.info("Finished combining transcriptions.")

    except Exception as e:
        logging.error(f"Error during the transcription process for {audio_path}: {e}", exc_info=True)
        full_transcription = "[Transcription Error: Overall process failed]"
    finally:
        if temp_dir.startswith(tempfile.gettempdir()) and "coursegen_audio_" in temp_dir:
             try:
                 os.rmdir(temp_dir) # Only works if empty
                 logging.info(f"Attempted to remove temporary audio directory: {temp_dir}")
             except OSError as rmdir_e:
                 logging.warning(f"Could not remove temp directory {temp_dir} (might not be empty or permission issue): {rmdir_e}")


    return full_transcription

def summarize_with_llm_api(transcription, hf_token, model_id="google/gemma-3-27b-it"):
    """
    Summarizes text using a specified LLM model via Hugging Face API.
    Handles retries.
    """
    if not hf_token:
        logging.error("Hugging Face API token is missing for summarization.")
        return "[Summarization Error: Missing API Token]"

    if not transcription or transcription.startswith("[Transcription Error"):
        logging.warning("Skipping summarization due to empty or error in transcription.")
        return "[Summarization Skipped: Invalid Transcription]"

    logging.info(f"Summarizing video contents using {model_id}...")

    API_URL = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {hf_token}"}

    max_words = 3000
    words = transcription.split()
    if len(words) > max_words:
        logging.warning(f"Transcription too long ({len(words)} words), truncating to {max_words} for summarization.")
        input_text = " ".join(words[:max_words])
    else:
        input_text = transcription

    prompt = f"""<s>[INST] Provide a concise summary of the following text:

    {input_text} [/INST]

    Summary:""" # Model expected format may vary

    # Adjust parameters based on model recommendations
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 512, # Max length of the summary
            "temperature": 0.6,
            "top_p": 0.9,
            "do_sample": True,
            "return_full_text": False # Get only the generated summary part
        }
    }

    max_retries = 3
    retry_delay = 10

    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=90) # Longer timeout for generation
            logging.debug(f"Summarization API status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                # Response format might be a list containing a dict
                if isinstance(result, list) and result:
                    summary = result[0].get("generated_text", "").strip()
                elif isinstance(result, dict):
                     summary = result.get("generated_text", "").strip() # Check direct dict response
                else:
                     summary = str(result) # Fallback
                logging.info("Successfully generated summary.")
                return summary
            elif response.status_code == 503:
                wait_time = int(response.headers.get("Retry-After", retry_delay))
                logging.warning(f"Summarization server busy (503). Retrying attempt {attempt + 1}/{max_retries} after {wait_time} seconds...")
                time.sleep(wait_time)
                retry_delay *= 1.5
            else:
                 logging.error(f"Summarization API Error {response.status_code}. Response: {response.text}")
                 # Don't retry on other errors
                 return f"[Summarization Error: API failed ({response.status_code})]"


        except requests.exceptions.RequestException as e:
            logging.error(f"Network/Request error during summarization (attempt {attempt + 1}): {e}", exc_info=True)
            if attempt >= max_retries - 1:
                return "[Summarization Error: Network/Request failed after retries]"
            time.sleep(retry_delay)

    logging.error(f"Summarization failed after {max_retries} attempts.")
    return "[Summarization Error: Failed after retries]"
def create_learning_content_api(summary, hf_token, model_id="google/gemma-3-27b-it"):
    """
    Creates learning module content based on summary using LLM API.
    Handles retries.
    """
    if not hf_token:
        logging.error("Hugging Face API token is missing for content generation.")
        return "[Learning Content Error: Missing API Token]"

    if not summary or summary.startswith("[Summarization Error") or summary.startswith("[Summarization Skipped"):
        logging.warning("Skipping learning content generation due to invalid summary.")
        return "[Learning Content Skipped: Invalid Summary]"

    logging.info(f"Generating learning module contents using {model_id}...")

    API_URL = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {hf_token}"}


    # Create a prompt for educational content
    prompt = f"""<s>[INST] Based on the following summary of a video:

    {summary}

    Create educational content structured as follows:
    1.  **Introduction:** Briefly introduce the main topic.
    2.  **Key Concepts:** Explain the core ideas or terms discussed.
    3.  **Main Learning Points:** List the key takeaways or skills presented.
    4.  **Reflection Questions:** Pose 2-3 questions to encourage deeper thinking about the content.

    Format the output clearly using markdown. [/INST]

    **Learning Module Content:**
    """ # Using the model's instruction format

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 1024, # Allow for more detailed content
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True,
            "return_full_text": False # Get only the generated part
        }
    }

    max_retries = 3
    retry_delay = 12

    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=120) # Even longer timeout
            logging.debug(f"Learning Content API status: {response.status_code}")

            if response.status_code == 200:
                 result = response.json()
                 # Handle potential response formats
                 if isinstance(result, list) and result:
                    content = result[0].get("generated_text", "").strip()
                 elif isinstance(result, dict):
                     content = result.get("generated_text", "").strip()
                 else:
                    content = str(result)
                 logging.info("Successfully generated learning content.")
                 return content
            elif response.status_code == 503:
                wait_time = int(response.headers.get("Retry-After", retry_delay))
                logging.warning(f"Learning content server busy (503). Retrying attempt {attempt + 1}/{max_retries} after {wait_time} seconds...")
                time.sleep(wait_time)
                retry_delay *= 1.5
            else:
                logging.error(f"Learning Content API Error {response.status_code}. Response: {response.text}")
                return f"[Learning Content Error: API failed ({response.status_code})]"

        except requests.exceptions.RequestException as e:
             logging.error(f"Network/Request error during content generation (attempt {attempt + 1}): {e}", exc_info=True)
             if attempt >= max_retries - 1:
                return "[Learning Content Error: Network/Request failed after retries]"
             time.sleep(retry_delay)

    logging.error(f"Learning content generation failed after {max_retries} attempts.")
    return "[Learning Content Error: Failed after retries]"

def process_youtube_video(youtube_url, hf_token):
    """
    End-to-end processing of YouTube video. Downloads, transcribes, summarizes,
    and generates learning content. Returns results as a dictionary.
    """
    results = {
        "transcription": None,
        "summary": None,
        "learning_content": None,
        "error": None,
        "file_paths": {} # Keep file paths if saving locally for debug
    }
    # Use a dedicated temporary directory for all processing artifacts of this video
    temp_processing_dir = tempfile.mkdtemp(prefix="coursegen_process_")
    logging.info(f"Created processing directory: {temp_processing_dir}")


    try:
        # --- Step 1: Download audio ---
        logging.info(f"Starting processing for: {youtube_url}")
        audio_path = download_youtube_audio(youtube_url, output_dir=temp_processing_dir)
        if audio_path:
             results["file_paths"]["audio"] = audio_path # Store path if needed
        else:
             raise Exception("Audio download failed.")


        # --- Step 2: Transcribe audio ---
        logging.info("Starting transcription...")
        transcription = transcribe_full_audio(audio_path, hf_token)
        results["transcription"] = transcription


        # --- Step 3: Summarize transcription ---
        logging.info("Starting summarization...")
        summary = summarize_with_llm_api(transcription, hf_token)
        results["summary"] = summary

        # --- Step 4: Create learning content ---
        logging.info("Starting learning content generation...")
        learning_content = create_learning_content_api(summary, hf_token)
        results["learning_content"] = learning_content

        if transcription.startswith("[Transcription Error"):
             results["error"] = "Transcription failed. " + transcription
        if summary.startswith("[Summarization Error") or summary.startswith("[Summarization Skipped"):
             results["error"] = (results.get("error", "") + "Summarization failed/skipped. " + summary).strip()
        if learning_content.startswith("[Learning Content Error") or learning_content.startswith("[Learning Content Skipped"):
             results["error"] = (results.get("error", "") + "Learning content generation failed/skipped. " + learning_content).strip()

        if results["error"]:
             logging.error(f"Processing completed with errors for {youtube_url}: {results['error']}")
        else:
             logging.info(f"Processing completed successfully for {youtube_url}")


    except Exception as e:
        logging.error(f"Critical error during video processing for {youtube_url}: {e}", exc_info=True)
        results["error"] = f"An unexpected error occurred during processing: {str(e)}"
        # Ensure partial results are still returned if available
        results["transcription"] = results.get("transcription", "[Processing Error]")
        results["summary"] = results.get("summary", "[Processing Error]")
        results["learning_content"] = results.get("learning_content", "[Processing Error]")

    finally:
        if os.path.exists(temp_processing_dir):
            try:
                import shutil
                shutil.rmtree(temp_processing_dir)
                logging.info(f"Removed processing directory: {temp_processing_dir}")
            except Exception as cleanup_e:
                logging.warning(f"Could not remove processing directory {temp_processing_dir}: {cleanup_e}")

    return results

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Process YouTube video into learning content (for testing)')
    parser.add_argument('--url', type=str, required=True, help='YouTube video URL')
    parser.add_argument('--output_dir', type=str, default=None, help='(Optional) Directory to save temporary files if needed for debugging') # Changed default

    args = parser.parse_args()

    # Get token from environment (priority) or argument (fallback, less secure)
    hf_token = os.environ.get("HF_API_TOKEN")
    #     return 1
    if not hf_token:
         print("Error: Hugging Face API token not provided. Set HF_API_TOKEN environment variable.")
         return 1


    # Process the YouTube video
    print(f"Processing video (local test): {args.url}")
    results = process_youtube_video(args.url, hf_token) # Pass token

    # Print results (or handle them as needed)
    print("\n--- Processing Results ---")
    if results.get("error"):
        print(f"Error: {results['error']}")
    print(f"Transcription: {'Provided' if results.get('transcription') and not results['transcription'].startswith('[') else 'Failed/Not Provided'}")
    # print(f"Transcription Text:\n{results.get('transcription', 'N/A')[:200]}...\n") # Print snippet
    print(f"Summary: {'Provided' if results.get('summary') and not results['summary'].startswith('[') else 'Failed/Not Provided'}")
    # print(f"Summary Text:\n{results.get('summary', 'N/A')[:200]}...\n")
    print(f"Learning Content: {'Provided' if results.get('learning_content') and not results['learning_content'].startswith('[') else 'Failed/Not Provided'}")
    # print(f"Learning Content Text:\n{results.get('learning_content', 'N/A')[:300]}...\n")

    if results.get("error"):
        print("Processing failed.")
        return 1
    else:
        print("Processing completed successfully!")
        return 0

if __name__ == "__main__":
    main()