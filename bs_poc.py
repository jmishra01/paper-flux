import bs4
# import requests
#
# url = "https://arxiv.org/abs/2602.11156"
#
#
# req = requests.get(url)
#
# content = req.text


with open("arxiv_url.txt", "r") as f:
    content = ''.join(f.readlines())

    # print(content)



parser = bs4.BeautifulSoup(content, "html.parser")

abs_id_parsed = parser.find("div", {"id": "abs"})

title = abs_id_parsed.find("h1", {"class": "title"})
print(title.text)

authors = abs_id_parsed.find("div", {"class": "authors"})

authors_list = authors.find_all("a")
for author in authors_list:
    print(author.text)


# abstract
abstract = parser.find("blockquote", {"class": "abstract"})
print(abstract.text)
