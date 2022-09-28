import requests
from bs4 import BeautifulSoup
from datetime import datetime
import yaml
import pathlib

import re

# ----------------------------------------
URLS = [
    "https://docs.microsoft.com/en-us/typography/opentype/spec/features_ae",
    "https://docs.microsoft.com/en-us/typography/opentype/spec/features_fj",
    "https://docs.microsoft.com/en-us/typography/opentype/spec/features_ko",
    "https://docs.microsoft.com/en-us/typography/opentype/spec/features_pt",
    "https://docs.microsoft.com/en-us/typography/opentype/spec/features_uz",
]

OUTPUT_PATH = "./feature_descriptions.yaml"

out = {}
for url in URLS:
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    data = []
    tags = soup.find_all('h2')
    for tag in tags:
        tag_name_str = re.match("Tag: '(....)'", tag.text)
        if tag_name_str:
            tag_data = {}
            tag_name = tag_name_str[1]
            descriptions = tag.find_next_siblings(['p', 'h2'])

            for d in descriptions:
                if d.name == "h2":
                    break
                title_item = d.em
                if title_item:
                    title = title_item.get_text(strip=True)
                    title_item.extract()
                    content = d.get_text(strip=True)
                    title = title.strip()
                    title = title.strip(":")
                    title = title.lower()
                    tag_data[title] = content
            if len(tag_data.keys()) > 0:
                out[tag_name] = tag_data

        if tag_name == "ss01":
            for i in range(1, 21):
                add_tag_data = tag_data.copy()
                tag_name = f"ss{i:02}"
                add_tag_data["friendly name"] = f"Stylistic Set {i}"
                out[tag_name] = add_tag_data


out_path = pathlib.Path(__file__).parent / OUTPUT_PATH
with open(out_path, "w+") as f:
    yaml.dump(out, f)

print("All done!")
