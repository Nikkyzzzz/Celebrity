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

warnings.filterwarnings('ignore')

# Configure the page
st.set_page_config(
    page_title="Celebrity News Sentiment Analyzer",
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

# Load local Lottie file (fallback)
def load_lottie_file(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

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
    /* Celebrity header/card */
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
    /* Make Streamlit progress bar match theme */
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }

    /* Ensure metric text is visible and aligned inside custom card */
    .metric-card .stMetric {
        width: 100%;
    }
    .metric-card .css-1v0mbdj e1fqkh3o0 { color: #111; }

    /* Smaller screens adjustments */
    @media (max-width: 800px) {
        .main-header { font-size: 2rem; }
        .sub-header { font-size: 1.1rem; }
        .celebrity-card h2 { font-size: 1.25rem; }
    }
    </style>
    """, unsafe_allow_html=True)

def search_google_news(celebrity_name, months=3):
    """
    Search Google News for celebrity news from past months
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months*30)

    # Format dates for Google News (use ISO YYYY-MM-DD which works better in searches)
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
                st.info("No results with date filters — showing broader search results.")
            except Exception:
                # If fallback also fails, just return what we have (empty)
                return news_articles

        return news_articles
        
    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")
        return []

def analyze_sentiment(text):
    """
    Analyze sentiment of text using TextBlob
    """
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity
    
    if polarity > 0.1:
        return "Positive", polarity, "😊"
    elif polarity < -0.1:
        return "Negative", polarity, "😞"
    else:
        return "Neutral", polarity, "😐"

def get_news_from_multiple_sources(celebrity_name):
    """
    Get news from multiple sources (simulated for demo)
    In a real app, you'd integrate with news APIs
    """
    # This is a simplified version. In production, use news APIs like:
    # NewsAPI, Bing News Search, or Google News API
    
    articles = search_google_news(celebrity_name)
    
    # Add sentiment analysis to each article
    for article in articles:
        sentiment, score, emoji = analyze_sentiment(article['title'])
        article['sentiment'] = sentiment
        article['sentiment_score'] = score
        article['emoji'] = emoji
    
    return articles

def display_sentiment_stats(articles):
    """
    Display sentiment statistics with enhanced visuals
    """
    if not articles:
        return
    
    sentiments = [article['sentiment'] for article in articles]
    sentiment_counts = pd.Series(sentiments).value_counts()
    
    total_articles = len(articles)
    positive_count = sentiments.count("Positive")
    negative_count = sentiments.count("Negative")
    neutral_count = sentiments.count("Neutral")
    
    # Create columns for metrics and display custom HTML cards so labels/value appear inside the boxes
    col1, col2, col3, col4 = st.columns(4)

    # Safely compute percentages
    def pct(count):
        return f"{(count/total_articles*100):.1f}%" if total_articles > 0 else "0.0%"

    with col1:
        html = f'''<div class="metric-card"><div style="text-align:left; width:100%"><div class="metric-card-title">Total Articles</div><div class="metric-card-value">{total_articles}</div></div></div>'''
        st.markdown(html, unsafe_allow_html=True)

    with col2:
        html = f'''<div class="metric-card"><div style="text-align:left; width:100%"><div class="metric-card-title">Positive</div><div class="metric-card-value">{positive_count}</div><div class="metric-card-sub">{pct(positive_count)}</div></div></div>'''
        st.markdown(html, unsafe_allow_html=True)

    with col3:
        html = f'''<div class="metric-card"><div style="text-align:left; width:100%"><div class="metric-card-title">Negative</div><div class="metric-card-value">{negative_count}</div><div class="metric-card-sub">{pct(negative_count)}</div></div></div>'''
        st.markdown(html, unsafe_allow_html=True)

    with col4:
        html = f'''<div class="metric-card"><div style="text-align:left; width:100%"><div class="metric-card-title">Neutral</div><div class="metric-card-value">{neutral_count}</div><div class="metric-card-sub">{pct(neutral_count)}</div></div></div>'''
        st.markdown(html, unsafe_allow_html=True)
    
    # Create visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart
        if total_articles > 0:
            fig_pie = px.pie(
                values=[positive_count, negative_count, neutral_count],
                names=['Positive', 'Negative', 'Neutral'],
                title='Sentiment Distribution',
                color=['Positive', 'Negative', 'Neutral'],
                color_discrete_map={
                    'Positive': '#28a745',
                    'Negative': '#dc3545',
                    'Neutral': '#6c757d'
                }
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Bar chart
        if total_articles > 0:
            fig_bar = px.bar(
                x=['Positive', 'Negative', 'Neutral'],
                y=[positive_count, negative_count, neutral_count],
                title='Sentiment Count',
                color=['Positive', 'Negative', 'Neutral'],
                color_discrete_map={
                    'Positive': '#28a745',
                    'Negative': '#dc3545',
                    'Neutral': '#6c757d'
                },
                labels={'x': 'Sentiment', 'y': 'Count'}
            )
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

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

def main():
    # Add custom CSS
    add_custom_css()
    
    # Header with enhanced design
    st.markdown('<h1 class="main-header">📰 Celebrity News Sentiment Analyzer</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Get insights about public perception through news sentiment analysis</p>', unsafe_allow_html=True)
    
    # Sidebar with enhanced design
    with st.sidebar:
        st.markdown("""
        <div style="background-color: #1f77b4; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
            <h2 style="color: white; margin: 0;">🔍 Search Settings</h2>
        </div>
        """, unsafe_allow_html=True)
        
        celebrity_name = st.text_input("Enter Celebrity Name", "Taylor Swift", help="Enter the name of the celebrity you want to analyze")
        
        # Add time range selector
        time_range = st.select_slider(
            "Time Range",
            options=["1 month", "2 months", "3 months", "6 months", "1 year"],
            value="3 months"
        )
        
        # Add number of articles selector
        max_articles = st.slider("Maximum Articles", min_value=5, max_value=50, value=20, help="Limit the number of articles to analyze")
        
        st.markdown("---")
        
        # Add information section
        with st.expander("ℹ️ About This App"):
            st.markdown("""
            This app analyzes news sentiment about celebrities by:
            - Scraping recent news articles
            - Analyzing title sentiment using TextBlob
            - Providing visual insights into public perception
            
            **How it works:**
            1. Enter a celebrity name
            2. Click "Analyze News Sentiment"
            3. View sentiment statistics and articles
            4. Filter by sentiment type
            5. Download results if needed
            """)
        
        # Add tips
        with st.expander("💡 Tips for Better Results"):
            st.markdown("""
            - Use full celebrity names for more accurate results
            - Try different spellings if no articles are found
            - Check the sentiment score for nuanced analysis
            - Consider cultural context when interpreting results
            """)
    
    # Main content area
    # Only run the search when the user clicks the button to avoid automatic runs on page load
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        analyze_button = st.button(
            "🔍 Analyze News Sentiment", 
            use_container_width=True,
            type="primary"
        )
    
    if analyze_button:
        if not celebrity_name.strip():
            st.error("Please enter a celebrity name!")
            return
        
        # Add progress bar for better UX
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Searching for news articles...")
        progress_bar.progress(25)
        
        articles = get_news_from_multiple_sources(celebrity_name)
        
        status_text.text("Analyzing sentiment...")
        progress_bar.progress(75)
        
        if not articles:
            progress_bar.progress(100)
            status_text.text("Analysis complete!")
            time.sleep(0.5)
            progress_bar.empty()
            status_text.empty()
            
            st.warning(f"No news articles found for '{celebrity_name}' in the selected time range.")
            st.info("Try searching for a different celebrity or check the spelling.")
            return
        
        progress_bar.progress(100)
        status_text.text("Analysis complete!")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        # Display celebrity card
        st.markdown(f"""
        <div class="celebrity-card">
            <h2>🎭 Analyzing: {celebrity_name}</h2>
            <p>Found {len(articles)} news articles from the past {time_range}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display statistics with enhanced visuals
        st.subheader("📊 Sentiment Overview")
        display_sentiment_stats(articles)
        
        # Create DataFrame for better display
        df = pd.DataFrame(articles)
        
        # Display articles by sentiment
        st.subheader("📋 News Articles")
        
        # Filter options
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            sentiment_filter = st.selectbox(
                "Filter by Sentiment",
                ["All", "Positive", "Negative", "Neutral"],
                help="Filter articles by sentiment type"
            )
        
        # Display articles with enhanced UI
        display_articles_with_sentiment(articles, sentiment_filter)
        
        # Download option
        st.subheader("💾 Download Results")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"{celebrity_name.replace(' ', '_')}_news_analysis.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Raw data view
        with st.expander("View Raw Data"):
            st.dataframe(df, use_container_width=True)
    
    # Add footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #636363;'>Built with ❤️ using Streamlit | Celebrity News Sentiment Analyzer</p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
