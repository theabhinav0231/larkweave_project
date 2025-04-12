from flask import Flask, render_template
import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)
products = [
    {
        "id": 1,
        "title": "Hand-Carved Wooden Bowl",
        "description": "Made from reclaimed maple wood using traditional carving techniques learned from Master J. Smith.",
        "learner_name": "Alex Chen",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSjIVVZ0_Ljnlb0vdBSjIIGp1AWHutpWUepdQ&s",
        "category": "Woodworking"
    },
    {
        "id": 2,
        "title": "Woven Tapestry Wall Hanging",
        "description": "Complex patterns achieved through techniques taught by artisan weaver Elena Petrova. Natural dyed wool.",
        "learner_name": "Priya Sharma",
        "image_url": "https://m.media-amazon.com/images/I/81rQmbSXQgS.jpg",
        "category": "Textiles"
    },
    {
        "id": 3,
        "title": "Ceramic Glazed Vase Set",
        "description": "Featuring a unique crystalline glaze perfected under the mentorship of ceramicist Kenji Tanaka.",
        "learner_name": "Maria Garcia",
        "image_url": "https://m.media-amazon.com/images/I/71Lx0Or15aL._AC_UF894,1000_QL80_.jpg",
        "category": "Ceramics"
    },
        {
        "id": 4,
        "title": "Hand-Forged Metal Sculpture",
        "description": "Abstract piece exploring form and texture, created using blacksmithing skills passed down by G. Ivanov.",
        "learner_name": "Sam Johnson",
        "image_url": "https://i.etsystatic.com/8817633/r/il/681e22/4701029711/il_570xN.4701029711_cm33.jpg",
        "category": "Metalwork"
    },
     {
        "id": 5,
        "title": "Leather Bound Journal",
        "description": "Classic Coptic stitch binding and tooling, knowledge shared by bookbinder Anne Dubois.",
        "learner_name": "Ben Carter",
        "image_url": "https://m.media-amazon.com/images/I/71T-+g4-2EL.jpg",
        "category": "Leatherwork"
    },
    {
        "id": 6,
        "title": "Stained Glass Panel",
        "description": "Inspired by Art Nouveau, using leading techniques guided by glass artist M. Lévesque.",
        "learner_name": "Chloe Dubois",
        "image_url": "https://i.etsystatic.com/10835273/r/il/2d0752/1764738468/il_fullxfull.1764738468_bc1g.jpg",
        "category": "Glass Art"
    },
    {
    "id": 7,
    "title": "Silver Filigree Earrings",
    "description": "Intricate swirling patterns crafted using fine silver wire, a technique learned from master jeweler Kenjiro Sato.",
    "learner_name": "Isabelle Rossi",
    "image_url": "https://goswadeshi.in/cdn/shop/files/1b_6b259706-a208-4b9d-acee-cf32046993ac.jpg?v=1693807986",
    "category": "Jewelry"
  },
  {
    "id": 8,
    "title": "Hand-Painted Silk Scarf",
    "description": "Delicate floral design painted on pure silk using techniques taught by textile artist Mei Lin.",
    "learner_name": "David Miller",
    "image_url": "https://m.media-amazon.com/images/I/71TBWM948cL._AC_UY1100_.jpg",
    "category": "Textiles"
  },
  {
    "id": 9,
    "title": "Custom-Blended Perfume Set",
    "description": "A unique set of three perfumes created with essential oils and fragrance notes, guided by perfumer Anya Volkov.",
    "learner_name": "Sophia Rodriguez",
    "image_url": "https://www.theperfumebar.co.in/wp-content/uploads/2020/09/ezgif.com-webp-to-jpg.jpg",
    "category": "Aromatherapy"
  }
]


@app.context_processor
def inject_now():
    return {'now': datetime.datetime.utcnow}

@app.route('/')
@app.route('/marketplace')
def marketplace():
    """Renders the marketplace page with product data."""
    return render_template('marketplace.html', products=products)

if __name__ == '__main__':
    app.run()