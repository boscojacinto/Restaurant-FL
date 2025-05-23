from transformers import pipeline

summarizer = pipeline("summarization", model="lidiya/bart-large-xsum-samsum")
conversation = '''
John: I am looking for tasty ramen, cooked in the traditional way. Can you provide instructions to make ramen?.
Bot:Okay, fantastic! Ramen is a truly rewarding dish to make, and doing it traditionally is absolutely worth the effort. Let’s dive in! It’s a labor of love, but the results – a rich, deeply flavorful broth and perfectly cooked noodles – are incredible.
	**Traditional Ramen Recipe - A Simplified Approach**
	This is a simplified version, aiming for a good traditional flavor without spending *days* on the broth.  A truly authentic ramen broth takes significantly longer, but this will give you a fantastic result in a reasonable amount of time.
	**Yields:** 2-3 servings
	**Prep Time:** 30 minutes
	**Cook Time:** 2-3 hours (mostly simmering)

	**Ingredients:**

	* **For the Broth (Tonkotsu-Style - Pork Bone Broth)**:
    * 2-3 lbs Pork Bones (Hock, Neck Bones, or a combination - ideally with some femur for richness)
    * 8 cups Water
    * 1 large Onion, quartered
    * 2-3 cloves Garlic, smashed
    * 2-inch piece of Ginger, sliced
    * 1 Scallion (green parts only), roughly chopped
    * 1 tbsp Black Peppercorns
    * 1 tsp Salt (adjust to taste later)

	* **For the Noodles:** (You can buy fresh ramen noodles, but homemade are amazing!)
    * 200g (7oz) Bread Flour
    * 1 tsp Salt
    * 70-80ml (2.4-2.7oz) Water (approximate - adjust as needed)

	* **Toppings (Suggestions - Customize to your liking!)**
    * Soft Boiled Eggs (Marinated in soy sauce is classic!)
    * Chashu Pork (Braised Pork Belly - recipe below)
    * Menma (Fermented Bamboo Shoots)
    * Scallions (thinly sliced)
    * Nori Seaweed Sheets
    * Chili Oil (for heat!)

**Instructions:**

	**1. Making the Broth:**
    * **Blanch the Bones:** Bring a large pot of water to a rolling boil. Add the pork bones and blanch them for 10-15 minutes. This removes impurities and creates a cleaner broth. Drain the bones and rinse them thoroughly under cold water.
    * **Simmer:** Return the bones to the pot. Add 8 cups of fresh water, onion, garlic, ginger, and peppercorns. Bring to a boil, then immediately reduce the heat to a *very* gentle simmer.  **Crucially, do not boil vigorously!**  This will make the broth cloudy.
    * **Skim Regularly:**  As the broth simmers, a white foam will rise to the surface. Skim this off regularly – this is crucial for a clear broth.  This takes about 1.5 - 2 hours.
    * **Long Simmer:** Continue simmering for at least 2-3 hours, or even longer for a deeper flavor. The longer you simmer, the more collagen will leach out of the bones, creating a richer, creamier broth.

	**2. Making the Noodles (While Broth Simmers - Quick Version)**
    * Combine flour and salt in a bowl.
    * Gradually add water, mixing until a shaggy dough forms.
    * Knead for 8-10 minutes until smooth and elastic.
    * Wrap in plastic wrap and let rest for 30 minutes.
    * Roll out thinly – about 1mm thick. Cut into noodles of desired width.

	**3. Finishing Up:**
    * Strain the broth through a fine-mesh sieve, discarding the solids. Season with salt to taste.
    * Cook the noodles according to package directions (usually 1-2 minutes in boiling water). Drain well.
    * Assemble the ramen: Place noodles in a bowl. Pour hot broth over noodles. Add your desired toppings.
'''

# conversation = '''Hannah: Hey, do you have Betty's number?
# Amanda: Lemme check
# Amanda: Sorry, can't find it.
# Amanda: Ask Larry
# Amanda: He called her last time we were at the park together
# Hannah: I don't know him well
# Amanda: Don't be shy, he's very nice
# Hannah: If you say so..
# Hannah: I'd rather you texted him
# Amanda: Just text him 🙂
# Hannah: Urgh.. Alright
# Hannah: Bye
# Amanda: Bye bye                                       
# '''
print(summarizer(conversation))
