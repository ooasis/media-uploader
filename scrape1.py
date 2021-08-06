import requests
from bs4 import BeautifulSoup

SRC_URL_TEMPLATE = "https://www.lwbcsd.org/主日信息/?_page={page}"


def scrape():
    for page in range(1, 15):
        OUT = open(f"audiolinks_{page}.psv", "w")
        url = SRC_URL_TEMPLATE.format(page=page)
        print(f"Fetch page: {url}")
        response = requests.get(url, headers={"User-Agent": "Python-3"})
        soup = BeautifulSoup(response.text, "html.parser")
        print(f"Fetched page")
        for div in soup.select(".pt-cv-view"):
            for a in div.find_all("a"):
                title = a.text
                detail_url = a.attrs["href"]
                print(f"Fetch detail page {detail_url}")
                response2 = requests.get(detail_url, headers={"User-Agent": "Python-3"})
                # flv_files = re.findall('"file":"(.+\.flv)"', response2.text.replace("\\u201d", ""))
                # for index, flv in enumerate(flv_files):
                #   href = f"https://www.lwbcsd.org{flv}"
                #   [month, day, year, other] = flv.split('/')[-1].split('-', 3)
                #   year = f"20{year}" if len(year) == 2 else year
                #   row = f"{title}|{year}-{month}-{day}|{index}|{href}\n"
                #   OUT.write(row)
                #   print(row)

                flv_files = []
                if len(flv_files) == 0:
                    soup2 = BeautifulSoup(response2.text, "html.parser")
                    print(f"No flv, try MP3")
                    for div2 in soup2.select(".entry-content"):
                        for index, a2 in enumerate(div2.find_all("a")):
                            href = a2.attrs["href"]
                            try:
                                [month, day, year, other] = href.split("/")[-1].split(
                                    "-", 3
                                )
                                year = f"20{year}" if len(year) == 2 else year
                                row = f"{title}|{year}-{month}-{day}|{index}|{href}\n"
                                OUT.write(row)
                                print(row)
                            except Exception as e:
                                print(f"Failed to process {href}")
        OUT.close()


if __name__ == "__main__":
    scrape()

