import pathlib
import csv
import json
import logging
import requests
from pygments import formatters, highlight, lexers

logging.basicConfig(
    level=logging.INFO, filename="YARS.log", format="%(asctime)s - %(message)s"
)


def display_results(results, title):

    try:
        print(f"\n{'-'*20} {title} {'-'*20}")

        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    formatted_json = json.dumps(item, sort_keys=True, indent=4)
                    colorful_json = highlight(
                        formatted_json,
                        lexers.JsonLexer(),
                        formatters.TerminalFormatter(),
                    )
                    print(colorful_json)
                else:
                    print(item)
        elif isinstance(results, dict):
            formatted_json = json.dumps(results, sort_keys=True, indent=4)
            colorful_json = highlight(
                formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter()
            )
            print(colorful_json)
        else:
            logging.warning(
                "No results to display: expected a list or dictionary, got %S",
                type(results),
            )
            print("No results to display.")

    except Exception as e:
        logging.error(f"Error displaying results: {e}")
        print("Error displaying results.")


def download_image(image_url, output_file: pathlib.Path, session=None):
    if session is None:
        session = requests.Session()

    try:
        response = session.get(image_url, stream=True)
        response.raise_for_status()
        with output_file.open("wb") as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        logging.info(f"Downloaded: {output_file}")
        return output_file
    except requests.RequestException as e:
        logging.error("Failed to download %s: %s", image_url, e)
        return None
    except Exception as e:
        logging.error("An error occurred while saving the image: %s", e)
        return None


def download_video(video_url, output_file: pathlib.Path, session=None):
    """
    Download a video from a Reddit URL to the specified output file.
    
    Args:
        video_url (str): The URL of the video to download
        output_file (str | pathlib.Path): The path where the video should be saved
        session (requests.Session, optional): An existing requests session to use
        
    Returns:
        pathlib.Path | None: The output file path if successful, None if failed
    """
    if session is None:
        session = requests.Session()
    
    # Create the parent directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Add headers that Reddit video servers expect
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.reddit.com/',
            'Accept': 'video/mp4,video/*;q=0.9,*/*;q=0.8'
        }
        
        response = session.get(video_url, stream=True, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Check if the response contains video content
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('video/'):
            logging.warning(f"URL does not appear to be a video: {video_url} (Content-Type: {content_type})")
        
        with output_file.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)
        
        logging.info(f"Downloaded video: {output_file}")
        return output_file
        
    except requests.RequestException as e:
        logging.error("Failed to download video %s: %s", video_url, e)
        return None
    except Exception as e:
        logging.error("An error occurred while saving the video: %s", e)
        return None


def export_to_json(data, filename="output.json"):
    try:
        with open(filename, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Data successfully exported to {filename}")
    except Exception as e:
        print(f"Error exporting to JSON: {e}")


def export_to_csv(data, filename="output.csv"):
    try:
        keys = data[0].keys()
        with open(filename, "w", newline="", encoding="utf-8") as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)
        print(f"Data successfully exported to {filename}")
    except Exception as e:
        print(f"Error exporting to CSV: {e}")