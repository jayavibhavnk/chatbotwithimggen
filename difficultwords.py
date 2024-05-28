import streamlit as st
import time
from youtube_transcript_api import YouTubeTranscriptApi
from streamlit_player import st_player
import requests
import re
from openai import OpenAI

def query_openai(query):
        client = OpenAI()
        completion = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": query}
        ],
        n = 1
        )
        return(completion.choices[0].message.content)

# List of languages for selection
LANGUAGES = {
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "pt": "Portuguese",
    "ru": "Russian",
    "fr": "French",
    "ja": "Japanese",
    "hi": "Hindi",
    "ar": "Arabic",
    "zh": "Chinese"
}

# Fetching common English words from GitHub
english_most_common_10k = 'https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa-no-swears.txt'
response = requests.get(english_most_common_10k)
common_words = set(response.text.strip().split('\n'))

def preprocess_text(text):
    # Remove punctuation except for hyphens and apostrophes
    text = re.sub(r'[^\w\s-]', '', text)
    return text

def fetch_youtube_transcript(video_id, language='en'):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript([language]).fetch()
        text = ' '.join([line['text'] for line in transcript])
        return transcript, text
    except Exception as e:
        st.error(f"Error fetching transcript: {e}")
        return None, None

def find_difficult_words(text):
    difficult_words = []
    words = text.split()
    for word in words:
        if word.lower() not in common_words:
            difficult_words.append(word)
    return difficult_words

def main():
    st.title('YouTube Transcript and Analysis Tool')

    # User inputs
    video_url = st.text_input("Enter a YouTube video URL:")
    target_language = st.selectbox('Select target language for translation:', list(LANGUAGES.keys()), format_func=lambda x: LANGUAGES[x])

    if video_url:
        video_id = video_url.split("v=")[-1]

        # Display video
        st_player(video_url, controls=True)

        # Display subtitles dynamically
        subtitle_placeholder = st.empty()
        translated_placeholder = st.empty()

        if st.button("Show Transcripts"):
            try:
                transcript_en, _ = fetch_youtube_transcript(video_id, 'en')
                transcript_target, _ = fetch_youtube_transcript(video_id, target_language)

                if transcript_en and transcript_target:
                    for i in range(len(transcript_en)):
                        original_subtitle = transcript_en[i]['text']
                        translated_subtitle = transcript_target[i]['text']
                        subtitle_placeholder.markdown(f"**Original (EN):** {original_subtitle}")
                        translated_placeholder.markdown(f"**Translated ({LANGUAGES[target_language]}):** {translated_subtitle}")
                        time.sleep(transcript_en[i]["duration"])
                        subtitle_placeholder.empty()
                        translated_placeholder.empty()
            except Exception as e:
                st.error(f"An error occurred: {e}")

        # Fetch and display transcripts
        if st.button('Fetch Transcript'):
            transcript, text = fetch_youtube_transcript(video_id, 'en')
            if transcript:
                st.write('Transcript fetched successfully.')
                st.text_area('Transcript:', value=text, height=200)
                text = preprocess_text(text)
                difficult_words = find_difficult_words(text)
                yoyo = query_openai("give me a summary of the youtube transcript: " + text + " You also have to give information about the tough words in the passage, explain whatever words you feel are difficult to underestand with respect to the context, tough words: " + ",".join(difficult_words))
                # if difficult_words:
                #     st.write('Difficult words found:')
                #     for word in difficult_words:
                #         st.write(word)
                # else:
                #     st.write('No difficult words found.')
                if yoyo:
                    st.write(yoyo)
            else:
                st.error('Failed to fetch transcript. Please check the video ID.')

if __name__ == "__main__":
    main()
