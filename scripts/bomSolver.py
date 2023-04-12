
import sys, getopt
exec(open('scripts/helper_functions.py').read())
exec(open('scripts/nexarClient.py').read())
exec(open('scripts/nexar_utils.py').read())

def main(argv):
    lookupNetsuite=False;
    lookupOctopart=False;
    inputFileName=''
    outputFileName='o.txt'
    MULTIPLIER=1;
    opts, args = getopt.getopt(argv,"hi:o:m:",["ifile=","ofile=","multiplier=","octopart","netsuite"])
    for opt, arg in opts:
        if opt == '-h':
            print ('bomSearch.py -i <inputfile> -o <outputfile> -m <multiplier> --octopart --netsuite')
            sys.exit()
        if opt in ("-i", "--ifile"):
            inputFileName = arg
            try:
                df = pd.read_csv(inputFileName,sep=';') #this is for each PCBA supplier
                try:
                    REQ=[]
                    for i in df.index:
                        REQ.append({'MPN':df.loc[i]['MPN'],'QTY':int(df.loc[i]['QTY'])});
                except:
                    print('Could not parse CSV file. Make sure it is formated properly')
                    print('MPN;QTY\nmpn1;qty1\npmn2;qty2\nmpn3;qty3\n')
                    print('Exiting')
                    sys.exit()
            except FileNotFoundError:
                print('The input file does not exist.')
                print('Exiting')
                sys.exit()
        elif opt in ("-o", "--ofile"):
            outputFileName = arg
        elif opt in ("--octopart"):
            lookupOctopart = True
        elif opt in ("--netsuite"):
            lookupNetsuite = True
        elif opt in ("-m","--multiplier"):
            MULTIPLIER = int(arg)
    #file containing the BOM
    df = pd.read_csv(inputFileName,sep=';')
    #generate Requirement list
    REQ=[];
    for i in df.index:
        REQ.append({'MPN':df.loc[i]['MPN'],'QTY':MULTIPLIER*int(df.loc[i]['QTY'])});
    if (lookupNetsuite==True):
        access_token = generate_access_token(app_id=APP_ID, scopes=SCOPES)
        headers = {
            'Authorization': 'Bearer ' + access_token['access_token']
        }
        params = {
            'top': 100, # max is 1000 messages per request
            'select': 'receivedDateTime,from,subject,hasAttachments',
            'orderby': 'receivedDateTime DESC',
            'filter': "receivedDateTime ge 2016-01-01T00:00:00Z and hasAttachments eq true and subject eq 'Inventory Detail by Bin'",
            'count': 'true'
        }

        response = requests.get(GRAPH_API_ENDPOINT + '/me/mailFolders/inbox/messages', headers=headers, params=params)
        if response.status_code != 200:
            raise Exception(response.json())
        response_json = response.json()
        emails = response_json['value']
        email_id = emails[0]['id']
        download_email_attachments(email_id, headers, r'data')
        #Checking all netsuite parts first, including substitutes
        dfinv=pd.read_csv('data/searchresults.csv')
        IHI={}
        for i in range(len(REQ)):
            MPN=REQ[i]['MPN']
            try:
                QCODE=MPN2Q[MPN]
                IHI[MPN]=lookPartInNetsuiteReport(QCODE,dfinv)
            except:
                IHI[MPN]=[]
            for sub in getSubs(MPN):
                try:
                    QCODE=MPN2Q[sub]
                    IHI[sub]=lookPartInNetsuiteReport(QCODE,dfinv)
                except:
                    IHI[sub]=[]
        #write results in temp.
        json_object = json.dumps(IHI, indent=4)
        with open("temp/IHI.json", "w") as outfile:
            outfile.write(json_object)
        f = open('data/IHI.json')
        IHI0 = json.load(f)
        f.close()
        IHI0=updateDic(IHI0,IHI)
        json_object = json.dumps(IHI0, indent=4)
        with open("data/IHI.json", "w") as outfile:
            outfile.write(json_object)
    else:
        #load default one
        f = open('data/IHI.json')
        IHI = json.load(f)
        f.close()
    if (lookupOctopart==True):
        print('Searching components on octopart ...')
        OctoSearches={}
        for i in range(len(REQ)):
            MPN=REQ[i]['MPN']
            QTY=REQ[i]['QTY']
            variables = {'mpn': MPN}
            print(MPN)
            results = nexar.get_query(CUSTOM_QUERY, variables)
            OctoSearches[MPN]=results
            for sub in getSubs(MPN):
                variables = {'mpn': sub}
                results = nexar.get_query(CUSTOM_QUERY, variables)
                OctoSearches[sub]=results
        #save search results in temp folder
        json_object = json.dumps(OctoSearches, indent=4)
        with open("temp/OctoSearches.json", "w") as outfile:
            outfile.write(json_object)
        f = open('data/OctoSearches.json')
        OctoSearches0 = json.load(f)
        f.close()
        OctoSearches0=updateDic(OctoSearches0,OctoSearches)
        json_object = json.dumps(OctoSearches0, indent=4)
        with open("data/OctoSearches.json", "w") as outfile:
            outfile.write(json_object)
    else:
        f = open('data/OctoSearches.json')
        OctoSearches = json.load(f)
        f.close()
    #Get TIERS to filter suppliers
    TIERLISTS=[];
    TIERLISTS.append(getSellerOctoUID(ST1))
    TIERLISTS.append(getSellerOctoUID(ST2))
    makeNewReport(REQ,IHI,OctoSearches,TIERLISTS,outputFileName)


if __name__ == "__main__":

    main(sys.argv[1:])
