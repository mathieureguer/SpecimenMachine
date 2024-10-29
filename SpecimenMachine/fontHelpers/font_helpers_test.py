import hyperglot.parse
import hyperglot.languages
import hyperglot.main

langs = hyperglot.languages.Languages(strict=False)
print(langs)


l = langs["fra"]
print(l["speakers"])

