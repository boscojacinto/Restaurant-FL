# Restaurant-FL: An automated Restaurant success prediction model(federated learning) using natural language based unstructured feature extraction and heterogeneous graph transfomers to capture high-order interactions between restaurants, customers and locality

Traditional restaurant success prediction models rely on restaurant datasets with fixed features like food type, ratings etc and a bunch of customer statistics like food preference, avg spend, demographric etc usually queried as a feedback questionnare with multiple choice answers.

What if a rich unstructure feature set can be captured through the medium of a fun natural conversation with the customer about the current dish, the restaurant menu, the customers likings and cravings, a brief history about the cuisine, any suggestions about the restaurant service etc. while making the conversational friendly, knowledgable and free flowing.

Introducing the restaurant's in-house friendly culinary expert, an efficient and light-weight personality that can answer questions about the restaurant, food facts, cuisine, food culture, basically anything about food.

Dont worry its just a Bot (gemma3:4b) that runs locally on the restaurant's PoS machine with the following system prompt
"""You are a friendly culinary expert with knowledge of food,
cooking techniques, regional cuisines, and global food culture.
You engage users in short but insightful, enjoyable conversations
about food, sharing recipes, ingredient tips, historical context,
modern trends and cooking wisdom.
You are enthusiastic, warm, and intelligent but is also considerate
of the user's time.
"""

![Using the Status-IM app](./Bot_Chat_01.png)

Customers are usually reluctant to provide feedback or honest opinions because they lack incentive to do so, this is where a natural non-pushy conversation can spark a drive to gain knowledge and facts about food. Additionally a small percentage of the price can be waivered by the restauarant adding economic incentive. Keeping the identities annoynomus can also help with the indulgence in the chat. In general storing data locally and not on server farms helps increase confidence. Also providing feedback of a recent but different restaurant visit can encourage a much honest review. Hence with the above in mind, the following point served as a foundational requirements for the design.

1. The Bot should run locally on the current restaurant PoS.
	*after a lot of experimentation we observed gemma3:4b has the right balance of capabilty and performace (currently tool calling doesn not work). We used ollama to serve multiple instances (currently 4 simultaneous chats)* 
2. The system should integrate with web3 for token incentives.
	*will be done in the future preferrably with native tokens on an L2 with order proofs*
3. The chat should be decentralized with complete annonymity.
	*we integrated with Status-IM p2p messanger which uses waku protocol*
4. The system should store customer ids and features in a local db
	*we store the customer and restaurant features as embeddings genrated form a short description (bot is prompted for the description at the end of the conversation) using an embedding model (nomic-embed-text) server locally on ollama *

![Using the Status-IM app](./Bot_Model_01.png)

For the Restaurant success predicition model the following were our requirements

1. Since the customer and restaurant insights do not leave the restaurant PoS 
   system, hence the model needs to train locally.
   *the restaurtant trains on the local dataset of customer and neighboring restaurants*

2. The model should learn first-order interaction between the customer, the 
   local restaurant and the neighboring restaurants.
   *we used a heterogeneous graph structure to represnts restaurant and customer with their respective features as nodes of two types. the edges between restaurant and customer represents the interaction between them. we also added area nodes and the edges between them and the restaurant represent the relative distance (locality) from the central area*

3. The model should learn higher-order interaction between restaurants, areas,
   localities and customers.
   *we used federated learning using Flower AI's framework to train the local graph on individual restaurant machines and then use FedAvg to aggregrates the local train weights to update the global model and global graph with all the restaurants, customers and area features and edges*

        






