import streamlit as st
import altair as alt
import pandas as pd
from collections import Counter
import json
import tweepy

st.title('Twitter分析アプリ')
st.write('''
ーーーこれは講座用です。ーーー\n
このアプリはTwitter APIを使った分析アプリです。\n
ユーザーのタイムラインを様々な角度から分析します。
''')

option = st.sidebar.selectbox(
    'オプション',
    ['API認証とユーザー名によるデータ取得', 'ユーザー名分析'],
)

if option == 'API認証とユーザー名によるデータ取得':
    uploaded_file = st.file_uploader('認証jsonファイルをアップロード', type=['json'])
    if uploaded_file is not None:
        auth_info = json.load(uploaded_file)
        consumer_key, consumer_secret, access_token, access_token_secret, bearer_token = auth_info.values()
        client = tweepy.Client(bearer_token=bearer_token)
        st.write('認証を完了しました。\n')
        username = st.text_input('ユーザー名で検索する場合はこちらにユーザー名（＠以下）を入力してください。', '03Imanyu')
        user_id = client.get_user(username=username).data.id

        st.write('### パラメータの設定')
        num_search_tweet = st.slider('検索件数', 0, 1000, 50)

        if st.button('データ取得'):
            message = st.empty()
            message.write('取得中です。')

            columns = ['時間', 'ツイート本文', 'いいね', 'リツイート', 'ID']
            excludes=['retweets', 'replies']
            tweet_fields=['created_at', 'public_metrics']
                        
            data = []
            for tweet in tweepy.Paginator(client.get_users_tweets, user_id, exclude=excludes, tweet_fields=tweet_fields).flatten(limit=num_search_tweet):
                text, _id, public_metrics, created_at,  = tweet['text'], tweet['id'], tweet['public_metrics'], tweet['created_at']
                datum = [created_at, text, public_metrics['like_count'], public_metrics['retweet_count'], _id]
                data.append(datum)
            
            df = pd.DataFrame(data=data, columns=columns)
            csv = df.to_csv(index=False).encode('utf-8')
            message.success('CSVファイルの出力が完了しました。')
            st.download_button(
                label='CSVファイルをダウンロード',
                data=csv,
                file_name = 'sample_data.csv',
                mime = 'text/csv'
            )
            st.dataframe(df)


if option == 'ユーザー名分析':
    uploaded_file = st.file_uploader('分析用csvファイルをアップロード', type=['csv'])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        hist = alt.Chart(df, title='いいね数の傾向').mark_bar(color='grey').encode(
            alt.X('いいね', bin=alt.Bin(extent=[0, df['いいね'].max()], step=5), title='いいね数'),
            alt.Y('count()', title='回数'),
            tooltip=('count()')
            )
        st.altair_chart(hist, use_container_width=True)

        df['時間'] = pd.to_datetime(df['時間'])
        df['時間'] = df['時間'].dt.tz_convert('Asia/Tokyo')
        df['時刻'] = df['時間'].dt.hour
        time_df = df[['いいね', '時刻']]
        time_df = time_df.sort_values(by=['時刻'])
        grouped = time_df.groupby('時刻')
        
        mean = grouped.mean()
        mean.columns = ['平均いいね数']
        size = grouped.size()
        base_time = pd.DataFrame([0]*24, index=list(range(0, 24)))
        base_time.index.name = '時刻'

        result = pd.concat([base_time, mean, size], axis=1).fillna(0)
        result.columns = ['0', '平均いいね数', 'ツイート数']
        result.drop('0', axis=1, inplace=True)
        result.reset_index(inplace=True)

        base = alt.Chart(result, title='時間帯ごとの傾向').encode(x='時刻:O')
        bar = base.mark_bar(color='grey').encode(y='平均いいね数:Q', tooltip='平均いいね数')
        line = base.mark_line(color='orange').encode(y='ツイート数:Q', tooltip='ツイート数')
        st.altair_chart(bar + line, use_container_width=True)

        df.loc[df['いいね'] >= 100, 'いいね評価'] = 'A'
        df.loc[(df['いいね'] < 100) & (df['いいね'] >= 50), 'いいね評価'] = 'B'
        df.loc[(df['いいね'] < 50) & (df['いいね'] >= 30), 'いいね評価'] = 'C'
        df.loc[(df['いいね'] < 30) & (df['いいね'] >= 10), 'いいね評価'] = 'D'
        df.loc[df['いいね'] < 10, 'いいね評価'] = 'E'

        df['文字数'] = df['ツイート本文'].str.len()
        grouped_fav = df.groupby('いいね評価')
        wordCountMean = grouped_fav.mean()[['文字数']]
        wordCountMean.reset_index(inplace=True)
        wordCountMean.columns = ['等級', '平均文字数']
        hist2 = alt.Chart(wordCountMean, title='等級と文字数の関係性').mark_bar(color='grey').encode(
            x='等級',
            y='平均文字数',
            tooltip=['平均文字数']
        )
        st.altair_chart(hist2)
