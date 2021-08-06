import re

import requests
from bs4 import BeautifulSoup

SRC_URL_TEMPLATE = (
    "https://www.lwbcsd.org/%e4%b8%bb%e6%97%a5%e4%bf%a1%e6%81%af/?_page={page}"
)


def scrape():
    for page in range(1, 2):
        OUT = open(f"youtube_{page-1}.psv", "w")
        url = SRC_URL_TEMPLATE.format(page=page)
        print(f"Fetch page: {url}")
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        print(f"Fetched page")
        for div in soup.select(".pt-cv-view"):
            for a in div.find_all("a"):
                title = a.text
                detail_url = a.attrs["href"]
                print(f"Fetch detail page {detail_url}")
                response2 = requests.get(detail_url)
                flv_files = re.findall(
                    '"file":"(.+\.flv)"', response2.text.replace("\\u201d", "")
                )
                soup2 = BeautifulSoup(response2.text, "html.parser")
                title = soup2.select(".entry-title")[0].text
                iframes = soup2.find_all("iframe")
                if not iframes or len(iframes) == 0:
                    print(f"Skip page as there is no iframe")
                    continue

                youtube_link = iframes[0]["src"].split("?")[0]
                desc = ""
                for ptext in soup2.find_all("p"):
                    if "主题经文" in ptext.text or "主題經文" in ptext.text:
                        desc = ptext.text.strip()
                        break
                row = f"{youtube_link}|{title}|{desc}\n"
                OUT.write(row)
                print(row)
        OUT.close()

if __name__ == "__main__":
    scrape()

