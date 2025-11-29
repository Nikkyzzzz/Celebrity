import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from textblob import TextBlob
import re
import time
from urllib.parse import quote
import warnings
import plotly.express as px
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
import json
import isodate  # For parsing YouTube duration
import os
from dotenv import load_dotenv

warnings.filterwarnings('ignore')

# YouTube API configuration (loaded from environment)
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"

# Configure the page
st.set_page_config(
    page_title="Celebrity News & YouTube Sentiment Analyzer",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Lottie animations
def load_lottie_url(url):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# Add custom CSS for styling
def add_custom_css():
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #636363;
        text-align: center;
        margin-bottom: 2rem;
    }
    .celebrity-card {
        background-color: #f0f2f6;
        padding: 1.25rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border-left: 6px solid #1f77b4;
        box-sizing: border-box;
        width: 100%;
        display: block;
        overflow: hidden;
    }
    .celebrity-card h2 { margin: 0 0 0.25rem 0; font-size: 1.75rem; }
    .celebrity-card p { margin: 0; color: #4b5563; }
    .positive-sentiment {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #28a745;
    }
    .negative-sentiment {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #dc3545;
    }
    .neutral-sentiment {
        background-color: #e2e3e5;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #6c757d;
    }
    .youtube-card {
        background-color: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background-color: #ffffff;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.06);
        min-height: 86px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .metric-card-title {
        font-size: 0.95rem;
        color: #6b7280;
    }
    .metric-card-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #111827;
        margin-top: 0.4rem;
    }
    .metric-card-sub {
        font-size: 0.8rem;
        color: #6b7280;
        margin-top: 0.4rem;
        display: inline-block;
        background: #f3f4f6;
        padding: 4px 8px;
        border-radius: 999px;
    }
    .video-thumbnail {
        border-radius: 8px;
        width: 100%;
        height: auto;
    }
    .tab-content {
        padding: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

def search_youtube_videos(celebrity_name, max_results=20):
    """
    Search YouTube for videos about the celebrity
    """
    try:
        # Search for videos
        search_url = f"{YOUTUBE_API_URL}/search"
        search_params = {
            'part': 'snippet',
            'q': f"{celebrity_name} news interview",
            'type': 'video',
            'maxResults': max_results,
            'order': 'relevance',
            'key': YOUTUBE_API_KEY
        }
        
        search_response = requests.get(search_url, params=search_params, timeout=10)
        search_data = search_response.json()
        
        if 'items' not in search_data:
            st.warning("No YouTube videos found or API quota exceeded.")
            return []
        
        video_ids = [item['id']['videoId'] for item in search_data['items'] if 'id' in item and 'videoId' in item['id']]
        
        if not video_ids:
            return []
        
        # Get video details
        videos_url = f"{YOUTUBE_API_URL}/videos"
        videos_params = {
            'part': 'snippet,statistics,contentDetails',
            'id': ','.join(video_ids),
            'key': YOUTUBE_API_KEY
        }
        
        videos_response = requests.get(videos_url, params=videos_params, timeout=10)
        videos_data = videos_response.json()
        
        youtube_videos = []
        
        for item in videos_data.get('items', []):
            try:
                # Get comments for the video (limited to 10 per video)
                comments = get_video_comments(item['id'])
                
                video_data = {
                    'id': item['id'],
                    'title': item['snippet'].get('title', 'No Title'),
                    'description': item['snippet'].get('description', 'No description'),
                    'channel_title': item['snippet'].get('channelTitle', 'Unknown Channel'),
                    'published_at': item['snippet'].get('publishedAt', 'Unknown date'),
                    'view_count': int(item['statistics'].get('viewCount', 0)),
                    'like_count': int(item['statistics'].get('likeCount', 0)),
                    'comment_count': int(item['statistics'].get('commentCount', 0)),
                    'thumbnail_url': item['snippet']['thumbnails']['high']['url'] if 'thumbnails' in item['snippet'] else '',
                    'duration': parse_duration(item['contentDetails'].get('duration', 'PT0M')),
                    'comments': comments,
                    'celebrity': celebrity_name,
                    'type': 'youtube'
                }
                
                # Clean description
                if len(video_data['description']) > 500:
                    video_data['description'] = video_data['description'][:500] + '...'
                
                # Analyze sentiment for title and description
                title_sentiment, title_score, title_emoji = analyze_sentiment(video_data['title'])
                desc_sentiment, desc_score, desc_emoji = analyze_sentiment(video_data['description'])
                
                # Analyze comments sentiment
                if comments:
                    comment_sentiments = [analyze_sentiment(comment)[1] for comment in comments]
                    avg_comment_sentiment = sum(comment_sentiments) / len(comment_sentiments)
                else:
                    avg_comment_sentiment = 0
                
                # Combined sentiment (weighted average)
                combined_score = (title_score * 0.4 + desc_score * 0.3 + avg_comment_sentiment * 0.3)
                combined_sentiment, _, combined_emoji = get_sentiment_from_score(combined_score)
                
                video_data.update({
                    'title_sentiment': title_sentiment,
                    'title_score': title_score,
                    'title_emoji': title_emoji,
                    'desc_sentiment': desc_sentiment,
                    'desc_score': desc_score,
                    'desc_emoji': desc_emoji,
                    'comment_sentiment_score': avg_comment_sentiment,
                    'combined_sentiment': combined_sentiment,
                    'combined_score': combined_score,
                    'combined_emoji': combined_emoji
                })
                
                youtube_videos.append(video_data)
                
            except Exception as e:
                continue
                
        return youtube_videos
        
    except Exception as e:
        st.error(f"YouTube API error: {str(e)}")
        return []

def get_video_comments(video_id, max_comments=10):
    """
    Get comments for a YouTube video
    """
    try:
        comments_url = f"{YOUTUBE_API_URL}/commentThreads"
        comments_params = {
            'part': 'snippet',
            'videoId': video_id,
            'maxResults': max_comments,
            'order': 'relevance',
            'key': YOUTUBE_API_KEY
        }
        
        comments_response = requests.get(comments_url, params=comments_params, timeout=10)
        comments_data = comments_response.json()
        
        comments = []
        for item in comments_data.get('items', []):
            try:
                comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
                # Clean HTML tags from comments
                comment = re.sub('<[^<]+?>', '', comment)
                comments.append(comment)
            except:
                continue
            
        return comments
        
    except Exception as e:
        # Comments might be disabled or API quota exceeded
        return []

def parse_duration(duration):
    """
    Parse ISO 8601 duration format
    """
    try:
        return str(isodate.parse_duration(duration))
    except:
        return "Unknown"

def analyze_sentiment(text):
    """
    Analyze sentiment of text using TextBlob
    """
    try:
        analysis = TextBlob(str(text))
        polarity = analysis.sentiment.polarity
        
        return get_sentiment_from_score(polarity)
    except:
        return "Neutral", 0, "😐"

def get_sentiment_from_score(score):
    """
    Get sentiment category from score
    """
    if score > 0.1:
        return "Positive", score, "😊"
    elif score < -0.1:
        return "Negative", score, "😞"
    else:
        return "Neutral", score, "😐"

def search_google_news(celebrity_name, months=3):
    """
    Search Google News for celebrity news from past months
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months*30)

    # Format dates for Google News
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    # Create search query
    query = f"{celebrity_name} celebrity news"
    encoded_query = quote(query)
    
    # Google News URL with date range
    url = f"https://news.google.com/rss/search?q={encoded_query}+after:{start_str}+before:{end_str}&hl=en-US&gl=US&ceid=US:en"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')

        news_articles = []

        for item in items[:20]:  # Limit to 20 articles
            try:
                title = item.title.text if item.title else "No title"
                link = item.link.text if item.link else "#"
                pub_date = item.pubDate.text if item.pubDate else "Unknown date"
                source = item.source.text if item.source else "Unknown source"

                # Clean the title
                title = re.sub(r'[^\x00-\x7F]+', ' ', title)

                news_articles.append({
                    'title': title,
                    'link': link,
                    'source': source,
                    'date': pub_date,
                    'celebrity': celebrity_name
                })

            except Exception:
                continue
                
        # If no articles were found with the date filters, try a broader search without dates
        if not news_articles:
            try:
                fallback_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
                response2 = requests.get(fallback_url, headers=headers, timeout=10)
                response2.raise_for_status()
                soup2 = BeautifulSoup(response2.content, 'xml')
                items2 = soup2.find_all('item')
                for item in items2[:40]:
                    try:
                        title = item.title.text if item.title else "No title"
                        link = item.link.text if item.link else "#"
                        pub_date = item.pubDate.text if item.pubDate else "Unknown date"
                        source = item.source.text if item.source else "Unknown source"
                        title = re.sub(r'[^\x00-\x7F]+', ' ', title)
                        news_articles.append({
                            'title': title,
                            'link': link,
                            'source': source,
                            'date': pub_date,
                            'celebrity': celebrity_name
                        })
                    except Exception:
                        continue
                # Inform the user in the Streamlit UI that a fallback was used
                if news_articles:
                    st.info("No results with date filters — showing broader search results.")
            except Exception:
                # If fallback also fails, just return what we have (empty)
                return news_articles

        return news_articles
        
    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")
        return []  # Return empty list instead of None

def get_news_from_multiple_sources(celebrity_name):
    """
    Get news from multiple sources - FIXED VERSION
    """
    articles = search_google_news(celebrity_name)
    
    # Ensure articles is always a list, even if search_google_news returns None
    if articles is None:
        articles = []
    
    # Add sentiment analysis to each article
    for article in articles:
        sentiment, score, emoji = analyze_sentiment(article['title'])
        article['sentiment'] = sentiment
        article['sentiment_score'] = score
        article['emoji'] = emoji
        article['type'] = 'news'
    
    return articles

def display_sentiment_comparison(news_articles, youtube_videos):
    """
    Display comparison between news and YouTube sentiment
    """
    if not news_articles and not youtube_videos:
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        if news_articles:
            news_sentiments = [article['sentiment'] for article in news_articles]
            news_positive = news_sentiments.count("Positive") / len(news_sentiments) * 100
            news_negative = news_sentiments.count("Negative") / len(news_sentiments) * 100
            news_neutral = news_sentiments.count("Neutral") / len(news_sentiments) * 100
            
            fig_news = go.Figure(data=[
                go.Bar(name='Positive', x=['News'], y=[news_positive], marker_color='#28a745'),
                go.Bar(name='Negative', x=['News'], y=[news_negative], marker_color='#dc3545'),
                go.Bar(name='Neutral', x=['News'], y=[news_neutral], marker_color='#6c757d')
            ])
            fig_news.update_layout(title='News Sentiment Distribution', barmode='stack')
            st.plotly_chart(fig_news, use_container_width=True)
        else:
            st.info("No news articles to display")
    
    with col2:
        if youtube_videos:
            yt_sentiments = [video['combined_sentiment'] for video in youtube_videos]
            yt_positive = yt_sentiments.count("Positive") / len(yt_sentiments) * 100
            yt_negative = yt_sentiments.count("Negative") / len(yt_sentiments) * 100
            yt_neutral = yt_sentiments.count("Neutral") / len(yt_sentiments) * 100
            
            fig_yt = go.Figure(data=[
                go.Bar(name='Positive', x=['YouTube'], y=[yt_positive], marker_color='#28a745'),
                go.Bar(name='Negative', x=['YouTube'], y=[yt_negative], marker_color='#dc3545'),
                go.Bar(name='Neutral', x=['YouTube'], y=[yt_neutral], marker_color='#6c757d')
            ])
            fig_yt.update_layout(title='YouTube Sentiment Distribution', barmode='stack')
            st.plotly_chart(fig_yt, use_container_width=True)
        else:
            st.info("No YouTube videos to display")

def display_youtube_videos(youtube_videos, sentiment_filter="All"):
    """
    Display YouTube videos with sentiment analysis
    """
    if not youtube_videos:
        st.info("No YouTube videos found for this celebrity.")
        return
    
    # Filter videos by sentiment
    if sentiment_filter != "All":
        filtered_videos = [video for video in youtube_videos if video['combined_sentiment'] == sentiment_filter]
    else:
        filtered_videos = youtube_videos
    
    st.markdown(f"**Showing {len(filtered_videos)} YouTube videos**")
    
    for video in filtered_videos:
        with st.container():
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if video['thumbnail_url']:
                    st.image(video['thumbnail_url'], use_column_width=True)
                st.markdown(f"**Views:** {video['view_count']:,}")
                st.markdown(f"**Likes:** {video['like_count']:,}")
                st.markdown(f"**Comments:** {video['comment_count']:,}")
                st.markdown(f"**Duration:** {video['duration']}")
            
            with col2:
                # Sentiment badges
                col2a, col2b, col2c = st.columns(3)
                with col2a:
                    sentiment_color = {"Positive": "🟢", "Negative": "🔴", "Neutral": "🟡"}
                    st.metric("Overall Sentiment", 
                             f"{sentiment_color[video['combined_sentiment']]} {video['combined_sentiment']}",
                             f"{video['combined_score']:.3f}")
                
                with col2b:
                    st.metric("Title Sentiment", 
                             f"{sentiment_color[video['title_sentiment']]} {video['title_sentiment']}",
                             f"{video['title_score']:.3f}")
                
                with col2c:
                    st.metric("Comments Sentiment", 
                             f"{video['comment_sentiment_score']:.3f}")
                
                st.markdown(f"### {video['title']}")
                st.markdown(f"**Channel:** {video['channel_title']}")
                st.markdown(f"**Published:** {video['published_at'][:10]}")
                
                with st.expander("View Description & Comments"):
                    st.markdown("**Description:**")
                    st.write(video['description'])
                    
                    st.markdown("**Top Comments:**")
                    if video['comments']:
                        for i, comment in enumerate(video['comments'][:5], 1):
                            comment_sentiment, comment_score, comment_emoji = analyze_sentiment(comment)
                            st.write(f"{i}. {comment_emoji} {comment[:200]}...")
                    else:
                        st.write("No comments available or comments disabled")
                
                # YouTube link
                st.markdown(f"[Watch on YouTube](https://www.youtube.com/watch?v={video['id']})")
            
            st.markdown("---")

def display_engagement_metrics(youtube_videos):
    """
    Display YouTube engagement metrics
    """
    if not youtube_videos:
        return
    
    df = pd.DataFrame(youtube_videos)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_views = df['view_count'].sum()
        st.metric("Total Views", f"{total_views:,}")
    
    with col2:
        total_likes = df['like_count'].sum()
        st.metric("Total Likes", f"{total_likes:,}")
    
    with col3:
        avg_sentiment = df['combined_score'].mean()
        st.metric("Avg. Sentiment", f"{avg_sentiment:.3f}")
    
    with col4:
        total_comments = df['comment_count'].sum()
        st.metric("Total Comments", f"{total_comments:,}")
    
    # Engagement chart
    if len(youtube_videos) > 1:
        fig = px.scatter(df, x='view_count', y='like_count', 
                         size='comment_count', color='combined_sentiment',
                         hover_data=['title'],
                         title='Video Engagement vs Sentiment',
                         color_discrete_map={
                             'Positive': '#28a745',
                             'Negative': '#dc3545', 
                             'Neutral': '#6c757d'
                         })
        st.plotly_chart(fig, use_container_width=True)

def main():
    # Add custom CSS
    add_custom_css()
    
    # Header with enhanced design
    st.markdown('<h1 class="main-header">📰🎬 Celebrity News & YouTube Sentiment Analyzer</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Get comprehensive insights from news and YouTube content</p>', unsafe_allow_html=True)
    
    # Sidebar with enhanced design
    with st.sidebar:
        st.markdown("""
        <div style="background-color: #1f77b4; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
            <h2 style="color: white; margin: 0;">🔍 Search Settings</h2>
        </div>
        """, unsafe_allow_html=True)
        
        celebrity_name = st.text_input("Enter Celebrity Name", "Taylor Swift", 
                                      help="Enter the name of the celebrity you want to analyze")
        
        # Data source selection
        data_sources = st.multiselect(
            "Data Sources",
            ["News Articles", "YouTube Videos"],
            default=["News Articles", "YouTube Videos"],
            help="Select which data sources to analyze"
        )
        
        # Add time range selector
        time_range = st.select_slider(
            "Time Range",
            options=["1 month", "2 months", "3 months", "6 months", "1 year"],
            value="3 months"
        )
        
        # Add number of articles/videos selector
        max_items = st.slider("Maximum Items per Source", min_value=5, max_value=30, value=15, 
                             help="Limit the number of articles/videos to analyze")
        
        st.markdown("---")
        
        # Add information section
        with st.expander("ℹ️ About This App"):
            st.markdown("""
            This app analyzes sentiment about celebrities from:
            - **News Articles**: Recent news coverage sentiment
            - **YouTube Videos**: Video titles, descriptions, and comments sentiment
            
            **Sentiment Analysis:**
            - News article titles
            - YouTube video titles and descriptions  
            - YouTube comments (top 10 per video)
            - Combined weighted sentiment scores
            """)
        
        # Add API status
        st.markdown("---")
        st.markdown("### 🔌 API Status")
        if YOUTUBE_API_KEY:
            st.success("YouTube API: ✅ Connected")
        else:
            st.error("YouTube API: ❌ Not Configured")

    # Main content area
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        analyze_button = st.button(
            "🔍 Analyze News & YouTube Sentiment", 
            use_container_width=True,
            type="primary"
        )
    
    if analyze_button:
        if not celebrity_name.strip():
            st.error("Please enter a celebrity name!")
            return
        
        # Initialize data containers
        news_articles = []
        youtube_videos = []
        
        # Add progress bar for better UX
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Fetch news articles
        if "News Articles" in data_sources:
            status_text.text("Searching for news articles...")
            news_articles = get_news_from_multiple_sources(celebrity_name)
            progress_bar.progress(33)
        
        # Fetch YouTube videos
        if "YouTube Videos" in data_sources:
            status_text.text("Searching YouTube videos...")
            youtube_videos = search_youtube_videos(celebrity_name, max_items)
            progress_bar.progress(66)
        
        status_text.text("Analyzing sentiment...")
        progress_bar.progress(100)
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        # Display results in tabs
        if news_articles or youtube_videos:
            # Display celebrity card
            st.markdown(f"""
            <div class="celebrity-card">
                <h2>🎭 Analyzing: {celebrity_name}</h2>
                <p>
                    Found {len(news_articles)} news articles and {len(youtube_videos)} YouTube videos
                    from the past {time_range}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Create tabs for different data sources
            tab1, tab2, tab3 = st.tabs(["📊 Overview", "📰 News Articles", "🎬 YouTube Videos"])
            
            with tab1:
                st.subheader("📈 Combined Analysis")
                
                # Display comparison
                if news_articles or youtube_videos:
                    display_sentiment_comparison(news_articles, youtube_videos)
                
                # Overall metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_items = len(news_articles) + len(youtube_videos)
                    st.metric("Total Items", total_items)
                
                with col2:
                    if news_articles:
                        news_positive = len([a for a in news_articles if a['sentiment'] == "Positive"])
                        st.metric("Positive News", news_positive)
                    else:
                        st.metric("Positive News", 0)
                
                with col3:
                    if youtube_videos:
                        yt_positive = len([v for v in youtube_videos if v['combined_sentiment'] == "Positive"])
                        st.metric("Positive Videos", yt_positive)
                    else:
                        st.metric("Positive Videos", 0)
                
                with col4:
                    if news_articles or youtube_videos:
                        total_positive = (len([a for a in news_articles if a['sentiment'] == "Positive"]) + 
                                        len([v for v in youtube_videos if v['combined_sentiment'] == "Positive"]))
                        overall_positive = total_positive / total_items * 100 if total_items > 0 else 0
                        st.metric("Overall Positive", f"{overall_positive:.1f}%")
                    else:
                        st.metric("Overall Positive", "0%")
                
                # YouTube engagement metrics
                if youtube_videos:
                    st.subheader("🎬 YouTube Engagement Metrics")
                    display_engagement_metrics(youtube_videos)
            
            with tab2:
                if news_articles:
                    st.subheader("📰 News Articles Analysis")
                    
                    # Filter options
                    col1, col2 = st.columns([1, 2])
                    with col2:
                        news_sentiment_filter = st.selectbox(
                            "Filter News by Sentiment",
                            ["All", "Positive", "Negative", "Neutral"],
                            key="news_filter"
                        )
                    
                    # Display news articles
                    display_articles_with_sentiment(news_articles, news_sentiment_filter)
                else:
                    st.info("No news articles found or news analysis not selected.")
            
            with tab3:
                if youtube_videos:
                    st.subheader("🎬 YouTube Videos Analysis")
                    
                    # Filter options
                    col1, col2 = st.columns([1, 2])
                    with col2:
                        yt_sentiment_filter = st.selectbox(
                            "Filter Videos by Sentiment",
                            ["All", "Positive", "Negative", "Neutral"],
                            key="youtube_filter"
                        )
                    
                    # Display YouTube videos
                    display_youtube_videos(youtube_videos, yt_sentiment_filter)
                else:
                    st.info("No YouTube videos found or YouTube analysis not selected.")
            
            # Download option
            st.subheader("💾 Download Results")
            
            # Combine data for download
            all_data = []
            for article in news_articles:
                all_data.append({
                    'type': 'news',
                    'title': article['title'],
                    'source': article['source'],
                    'date': article['date'],
                    'sentiment': article['sentiment'],
                    'sentiment_score': article['sentiment_score'],
                    'link': article['link']
                })
            
            for video in youtube_videos:
                all_data.append({
                    'type': 'youtube',
                    'title': video['title'],
                    'channel': video['channel_title'],
                    'published_at': video['published_at'],
                    'views': video['view_count'],
                    'likes': video['like_count'],
                    'comments': video['comment_count'],
                    'sentiment': video['combined_sentiment'],
                    'sentiment_score': video['combined_score'],
                    'link': f"https://www.youtube.com/watch?v={video['id']}"
                })
            
            if all_data:
                df = pd.DataFrame(all_data)
                csv = df.to_csv(index=False)
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.download_button(
                        label="Download Combined CSV",
                        data=csv,
                        file_name=f"{celebrity_name.replace(' ', '_')}_combined_analysis.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
        
        else:
            st.warning(f"No data found for '{celebrity_name}' across selected sources.")
            st.info("Try searching for a different celebrity or check the spelling.")
    
    # Add footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #636363;'>Built with ❤️ using Streamlit | Celebrity News & YouTube Sentiment Analyzer</p>",
        unsafe_allow_html=True
    )

def display_articles_with_sentiment(articles, sentiment_filter):
    """
    Display articles with enhanced UI based on sentiment
    """
    # Filter articles
    if sentiment_filter != "All":
        filtered_articles = [article for article in articles if article['sentiment'] == sentiment_filter]
    else:
        filtered_articles = articles
    
    # Display articles count
    st.markdown(f"**Showing {len(filtered_articles)} articles**")
    
    # Display articles
    for i, article in enumerate(filtered_articles):
        # Apply different styling based on sentiment
        sentiment_class = ""
        if article['sentiment'] == "Positive":
            sentiment_class = "positive-sentiment"
        elif article['sentiment'] == "Negative":
            sentiment_class = "negative-sentiment"
        else:
            sentiment_class = "neutral-sentiment"
        
        st.markdown(f'<div class="{sentiment_class}">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"### {article['emoji']} {article['title']}")
            st.markdown(f"**Source:** {article['source']} | **Date:** {article['date']}")
            
        with col2:
            sentiment_color = {
                "Positive": "🟢",
                "Negative": "🔴", 
                "Neutral": "🟡"
            }
            st.markdown(
                f"<h3 style='text-align: center;'>{sentiment_color[article['sentiment']]} {article['sentiment']}</h3>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"<p style='text-align: center;'>Score: {article['sentiment_score']:.3f}</p>",
                unsafe_allow_html=True
            )
        
        with st.expander("View Article Details"):
            st.markdown(f"**Title:** {article['title']}")
            st.markdown(f"**Source:** {article['source']}")
            st.markdown(f"**Published:** {article['date']}")
            st.markdown(f"**Sentiment:** {article['sentiment']} (Score: {article['sentiment_score']:.3f})")
            st.markdown(f"**Link:** [Read full article]({article['link']})")
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("")

if __name__ == "__main__":
    main()
