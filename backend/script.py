import xmltodict
import json

def build_database():
    with open("mplus_topics.xml", "rb") as f:
        data_dict = xmltodict.parse(f)
    
    formatted_data = {}
    # MedlinePlus topics are stored in a specific nested list
    topics = data_dict['health-topics']['health-topic']
    
    for topic in topics:
        title = topic['@title']
        
        summary = topic.get('full-summary', "No description available.")
        
        keywords = []
        if 'mesh-heading' in topic:
            headings = topic['mesh-heading']
            if isinstance(headings, list):
                keywords = [h['descriptor']['#text'].lower() for h in headings if 'descriptor' in h]
            else:
                keywords = [headings['descriptor']['#text'].lower()]

        formatted_data[title.lower().replace(" ", "_")] = {
            "name": title,
            "source": "MedlinePlus / NIH",
            "text": summary[:500] + "...", 
            "keywords": keywords
        }

    with open("medical_data.json", "w") as f:
        json.dump(formatted_data, f, indent=4)

if __name__ == "__main__":
    build_database()
