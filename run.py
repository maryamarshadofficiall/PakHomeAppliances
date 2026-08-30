from scrape_hub import scrape_daraz, scrape_official_site, scrape_youtube, add_facebook_reviews_manually

# ==== Jitne bhi naye sources se product add karna ho, yahan call karein ====

# 1) Daraz se
scrape_daraz("https://www.daraz.pk/products/NAYA-LINK.html", "PEL")

# 2) Official website se
# scrape_official_site("https://www.pel.com.pk/product-page", "PEL")

# 3) YouTube se (comments as reviews)
# scrape_youtube("https://www.youtube.com/watch?v=XXXXXXX", "PEL", "PEL InverterOn 1 Ton")

# 4) Facebook se (manually collected reviews paste karein)
# add_facebook_reviews_manually(
#     "https://facebook.com/post-link",
#     "PEL",
#     "PEL InverterOn 1 Ton",
#     ["yahan review 1", "yahan review 2", "yahan review 3"]
# )