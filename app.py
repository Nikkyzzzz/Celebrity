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
warnings.filterwarnings('ignore')

# Configure the page
st.set_page_config(
    page_title="Celebrity News Sentiment Analyzer",
    page_icon="📰",
    layout="wide"
)

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
    Display sentiment statistics
    """
    if not articles:
        return
    
    sentiments = [article['sentiment'] for article in articles]
    sentiment_counts = pd.Series(sentiments).value_counts()
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_articles = len(articles)
    positive_count = sentiments.count("Positive")
    negative_count = sentiments.count("Negative")
    neutral_count = sentiments.count("Neutral")
    
    with col1:
        st.metric("Total Articles", total_articles)
    
    with col2:
        st.metric("Positive", positive_count, f"{positive_count/total_articles*100:.1f}%")
    
    with col3:
        st.metric("Negative", negative_count, f"{negative_count/total_articles*100:.1f}%")
    
    with col4:
        st.metric("Neutral", neutral_count, f"{neutral_count/total_articles*100:.1f}%")

def main():
    # Header
    st.title("📰 Celebrity News Sentiment Analyzer")
    st.markdown("Get the latest news about any celebrity from the past 3 months with sentiment analysis!")
    
    # Sidebar
    st.sidebar.title("Settings")
    celebrity_name = st.sidebar.text_input("Enter Celebrity Name", "Taylor Swift")
    
    st.sidebar.markdown("---")
    st.sidebar.info(
        "This app scrapes news articles from the past 3 months and analyzes "
        "the sentiment of each article's title to give you insights about "
        "public perception."
    )
    
    # Main content
    # Only run the search when the user clicks the button to avoid automatic runs on page load
    if st.button("🔍 Analyze News Sentiment"):
        if not celebrity_name.strip():
            st.error("Please enter a celebrity name!")
            return
        
        with st.spinner(f"Searching for news about {celebrity_name}..."):
            articles = get_news_from_multiple_sources(celebrity_name)
        
        if not articles:
            st.warning(f"No news articles found for '{celebrity_name}' in the past 3 months.")
            st.info("Try searching for a different celebrity or check the spelling.")
            return
        
        # Display statistics
        st.subheader("📊 Sentiment Overview")
        display_sentiment_stats(articles)
        
        # Create DataFrame for better display
        df = pd.DataFrame(articles)
        
        # Display articles by sentiment
        st.subheader("📋 News Articles")
        
        # Filter options
        col1, col2 = st.columns([1, 4])
        with col1:
            sentiment_filter = st.selectbox(
                "Filter by Sentiment",
                ["All", "Positive", "Negative", "Neutral"]
            )
        
        # Filter articles
        if sentiment_filter != "All":
            filtered_articles = [article for article in articles if article['sentiment'] == sentiment_filter]
        else:
            filtered_articles = articles
        
        # Display articles
        for i, article in enumerate(filtered_articles):
            with st.container():
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
                
                st.markdown("---")
        
        # Download option
        st.subheader("💾 Download Results")
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"{celebrity_name.replace(' ', '_')}_news_analysis.csv",
            mime="text/csv"
        )
        
        # Raw data view
        with st.expander("View Raw Data"):
            st.dataframe(df)

if __name__ == "__main__":
    main()