import re


def scrape():
    with open("raw.psv", "r") as RAW:
        with open("audo.psv", "w") as OUT:
            for raw_file in RAW:
                raw_file = raw_file.strip()
                m = re.match(
                    r"^(\d{2})[-_](\d{2})[-_](\d{1,2})[^\d](.+)\.mp3$", raw_file
                )
                if m:
                    dt = f"20{m.group(3)}-{m.group(1)}-{m.group(2)}"
                    title = re.sub(r"\W+", " ", m.group(4)).strip()
                    # print(f"{dt}: {title}")
                else:
                    m = re.match(
                        r"^(\d{4})[-_](\d{2})[-_](\d{1,2})[^\d](.+).mp3$", raw_file
                    )
                    if m:
                        dt = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                        title = re.sub(r"\W+", " ", m.group(4)).strip()
                        # print(f"{dt}: {title}")
                    else:
                        title = None
                        print(f"Cannot parse {raw_file}")
                if title != None:
                    OUT.write(f"{dt}|{title}|{raw_file}\n")


if __name__ == "__main__":
    scrape()

