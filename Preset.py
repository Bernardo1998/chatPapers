import json


class Preset:
    '''
        This class handles records all papers that have been checked and all keywords/key papers to check rountinly.
    '''
    def __init__(self, rountin_config_path) -> None:
        self.rountine_config_path = rountin_config_path
        if self.rountine_config_path is not None:
            self.rountine_config = json.load(open(self.rountine_config_path))
        else:
            self.rountine_config = {"checked_paper":{'Title':[], 'URL':[]}, "preset_papers":{}}

    def change_preset(self):
        choice = 0
        prompt = "Do you want to add any search keyword to rountine preset? 1, add keywords; 2, remove keywords; 3, skip."
        while choice != 3:
            choice = int(input(prompt))
            if choice == 1:
                keyword = input("Please enter the search keywords you want.")
                self.add_preset(keyword)
            elif choice == 2:
                index_to_keyword = {}
                for i,k in enumerate(self.rountine_config.keys()):
                    print(f"{i}, {keyword}")
                    index_to_keyword[i] = k
                index = int(input("Please enter the index of existing keyword you want to remove."))
                self.delete_preset(index_to_keyword[index])
            elif choice == 3:
                _ = input("Press any key to continue.")
            else:
                print("Invalid prompt! Please choose from numbers above.")            


    def add_preset(self, keyword):
        self.rountine_config['preset_papers'].update({keyword:[]})

    def delete_preset(self, keyword):
        if keyword in self.rountine_config['preset_papers']:
            del self.rountine_config['preset_papers'][keyword]
        else:
            print(f"Keyword {keyword} does not exist! Removal not completed")

    def get_keywords(self):
        return self.rountine_config['preset_papers'].keys()
    
    def get_read(self):
        return self.rountine_config['checked_paper']
    
    def update_read(self, title, url):
        self.rountine_config['checked_paper']['Title'].append(title)
        self.rountine_config['checked_paper']['URL'].append(url)

    def save_preset(self):
        with open(self.rountine_config_path, 'w') as rtF:
            rtF.write(json.dumps(self.rountine_config_path))