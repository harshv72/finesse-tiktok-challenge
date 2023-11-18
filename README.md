# finesse-tiktok-challenge
This repository houses my solutions for Finesse's Software Engineering Challenge. The challenge is to accumulate data from Tiktok's fashion posts using different scrapping methods.

## About Challenge
Over the last years, the birthplace of fashion shifted from catwalks and magazines to social media. Consequently, social data constitutes the heart of FINESSE. <br/>
The goal of this challenge is to build a TikTok scraper that can retrieve fashion posts. Fashion posts can be identified by analyzing the comments, account, hashtags, etc.

## How to run the project?

#### Build

```sh
docker build . -t tiktok-challenge
```

#### Run

```sh
docker run -p 8000:8000 tiktok-challenge
```

- Running server with single process - single task for testing purpose.
- After running on the docker, service will be forwarded to localhost:8000

```code
Start Scrapping Task: http://localhost:8000/scrap
Check Scrapping Status: http://localhost:8000/status
Download Dumped File: http://localhost:8000/download/[path]
```
