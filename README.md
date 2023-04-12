# bomSolver
A suite of scripts to determine availability of parts in house or on octopart.
```
python3 scripts/bomSolver.py -i <inputfile> -o <outputfile> -m <multiplier> --octopart --netsuite
```

Option -m Multiplier allows to multiply all the quantities by an integer.

Option --octopart will perform a search on octopart. It is recommended to do it everytime, but nexar requests are limited to 1000 per month. Alternative credentials can be used, by modifying *nexar_utils.py*. If not used, the program will use the OcotoSearches.json file in the data folder. When used, this option will update the OctoSearches.json file.

Option --netsuite will perform a search in Qnergy inventory after downloading the daily Netsuite report. You will need to provide credential for netsuite.reports@qnergy.com. It is only necessary to use this option once per day. If not used, the program will use the IHI.json file in the data folder. When used, this option will update the IHI.json file..


## Dependencies :
If you use a conda virtual environment (recommended) use :
```
conda install pandas
pip3 install msal
conda install requests
```

## Folder structure :

### **scripts** folder:

-**bomSolver.py** : This is the main script. See above for help.

-**helper_functions.py** : A lot of different functions to retrieve data, parse it and generate reports. The function  *resolve.py*  is what determines priority of the different procurement options.

-**nexarClient.py** : A class provided by nexar to use their API.

-**nexar_utils.py** : Credentials and custom query to use the nexar API.

### **data** folder :
Contains various information necessary for the scripts to function properly. Some of it can be updated by the user.

-**substitutes.csv** : contains a list of equivalent parts. Option 1 is highest priority. **This file can be modified by users.**

-**MPN2QN.csv** : contains a list of components and their unique Qnergy inventory number. **This file can be modified by users.** Add to the list if new part is added to inventory.

-**IHI.json** : IHI stands for In House Inventory. This file dates from february 2023, ideally it needs to be regenerated every time as inventory changes daily. If not generated, this file will be used. The way the file is generated is through gui automation, only tested on safari browser with max zoom out on macbookpro (2560 × 1600). Use with caution. New generated file will be found in temp folder and can be reused by placing it in the data folder.

-**OctoSearches.json** : contains the extended results done on octopart through the nexar API. This can also be redone everytime with option --octopart but keep in mind this uses nexar credits. The generated file will be found in temp folder and can be reused by placing it in the data folder.

-**supplierTier1.txt** : Contains a list of most favourable suppliers. The most trusted supplier is on the first line. If the name doesn't match, the closest name will be suggested. Please refer to allSuppliers.csv to find the exact name. **This can be updated by user.**

-**supplierTier2.txt** : Contains a list of less favourable suppliers. The most trusted supplier is on the first line. If the name doesn't match, the closest name will be suggested. Please refer to allSuppliers.csv to find the exact name. **This can be updated by user.**

-**AllSuppliers.json** : contains a list of all the octopart suppliers and their unique ID. **Do not modify.**

-**AllManufactures.json** : contains a list of all the octopart manufactures and their unique ID. **Do not modify.**

### **temp** folder :

Contains temporary files for the octopart / netsuite searches and authentication token.

### **bom_example** folder :

Contains BOMs that can be used to test the program.
