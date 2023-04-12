import pandas as pd
import os,sys,time,json,re
from operator import itemgetter
import numpy as np
import requests
import base64
from typing import Dict
import requests
import webbrowser
from datetime import datetime
import msal

#Define colors for text output
class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[33m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

APP_ID='fdc904dc-83e1-4262-ae08-612e875c4ab1'
SCOPES = ['Mail.ReadWrite']
GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'

def generate_access_token(app_id, scopes):
    # Save Session Token as a token file
    access_token_cache = msal.SerializableTokenCache()
    # read the token file
    if os.path.exists('temp/ms_graph_api_token.json'):
        access_token_cache.deserialize(open("temp/ms_graph_api_token.json", "r").read())
        token_detail = json.load(open('temp/ms_graph_api_token.json',))
        token_detail_key = list(token_detail['AccessToken'].keys())[0]
        token_expiration = datetime.fromtimestamp(int(token_detail['AccessToken'][token_detail_key]['expires_on']))
        if datetime.now() > token_expiration:
            os.remove('temp/ms_graph_api_token.json')
            access_token_cache = msal.SerializableTokenCache()
    # assign a SerializableTokenCache object to the client instance
    client = msal.PublicClientApplication(client_id=app_id, token_cache=access_token_cache)
    accounts = client.get_accounts()
    if accounts:
        # load the session
        token_response = client.acquire_token_silent(scopes, accounts[0])
    else:
        # authetnicate your accoutn as usual
        flow = client.initiate_device_flow(scopes=scopes)
        print('user_code: ' + flow['user_code'])
        webbrowser.open('https://microsoft.com/devicelogin')
        token_response = client.acquire_token_by_device_flow(flow)
    with open('temp/ms_graph_api_token.json', 'w') as _f:
        _f.write(access_token_cache.serialize())
    return token_response


def download_email_attachments(message_id, headers, save_folder=os.getcwd()):
    try:
        response = requests.get(
            GRAPH_API_ENDPOINT + '/me/messages/{0}/attachments'.format(message_id),
            headers=headers
        )
        attachment_items = response.json()['value']
        for attachment in attachment_items:
            file_name = attachment['name']
            attachment_id = attachment['id']
            attachment_content = requests.get(
                GRAPH_API_ENDPOINT + '/me/messages/{0}/attachments/{1}/$value'.format(message_id, attachment_id),
                headers=headers
            )
            print('Saving file {0}...'.format(file_name))
            with open(os.path.join(save_folder, file_name), 'wb') as _f:
                _f.write(attachment_content.content)
        return True
    except Exception as e:
        print(e)
        return False
#
# def _workaround_write(text):
#     """
#     This is a work-around for the bug in pyautogui.write() with non-QWERTY keyboards
#     It copies the text to clipboard and pastes it, instead of typing it.
#     """
#     pyperclip.copy(text)
#     pyautogui.hotkey('command', 'v')
#     pyperclip.copy('')


#Import Rosetta Stone
df = pd.read_csv('data/MPN2QN.csv',sep=';')
MPN2Q={};
Q2MPN={};
for i in df.index:
    if pd.isna(df.loc[i]['QCODE']):
        MPN2Q[df.loc[i]['MPN']]='Undefined';
    else:
        MPN2Q[df.loc[i]['MPN']]=df.loc[i]['QCODE'];
        Q2MPN[df.loc[i]['QCODE']]=df.loc[i]['MPN'];

#Import Substitute dictionnary
df = pd.read_csv('data/substitutes.csv',sep=';')
subList=[];
for i in df.index:
    options=[];
    for j in range(len(df.columns)):
        if pd.isna(df.loc[i].iat[j])==False:
            options.append(df.loc[i].iat[j])
    subList.append(options)


def getSubs(part):
    """
    This function returns the list of all substitutes for a given part,
    with first element being the prefered one.
    """
    subs=[]
    for i in range(len(subList)):
        for j in range(len(subList[i])):
            if subList[i][j]==part:
                for k in range(len(subList[i])):
                    if subList[i][k]!=part:
                        subs.append(subList[i][k])
                return subs
    return subs

def lookInHouse(part,amount):
    #1 look in house
    print('    Looking for '+str(amount)+' parts in house.')
    remaining=amount
    available=0
    try:
        Qnumber=MPN2Q[part]
        try:
            locs=WHERE[Qnumber]
            for loc in locs:
                if loc[1]!='WESCO':
                    available+=loc[2]
                print('        ---> '+str(loc[2])+' at '+loc[0]+'(bin '+loc[1]+')')
            print('        '+str(available)+' parts available in Ogden.')
        except:
            print('Part is not in inventory.')
    except:
        print('        Part is not in NETSUITE.')
    remaining-=available
    if (remaining<=0):
        print('    Resolved.')
        return 0;
    else:
        print('        '+str(remaining)+' parts remaining.')
        substitutes=getSubs(part)
        if len(substitutes)==0:
            print('        No substitute available.')
        else:
            for sub in substitutes:
                available=0;
                try:
                    Qnumber=MPN2Q[sub]
                    print('        Substitute '+sub+' ('+str(Qnumber)+') :')
                    try:
                        locs=WHERE[Qnumber]
                        for loc in locs:
                            if loc[1]!='WESCO':
                                available+=loc[2]
                            print('        ---> '+str(loc[2])+' at '+loc[0]+'(bin '+loc[1]+')')
                        print('        '+str(available)+' parts available in Ogden.')
                    except:
                        print('Substitute is not in inventory.')
                except:
                    print('        Substitute '+sub+' not in NETSUITE.')
                remaining-=available
                if (remaining<=0):
                    print('    Resolved.')
                    return 0;
                else:
                    print('        '+str(remaining)+' parts remaining.')
    return remaining


def updateDic(DIC1,DIC2):
    '''
    This function is to update DIC1
    '''
    for key in DIC2.keys():
        DIC1[key]=DIC2[key]
    return DIC1

def lookPartInNetsuiteReport(QCODE,df):
    x=df['Name']==QCODE
    y=df[x]['On Hand']>0
    #df[x][y]
    o=[]
    for i,row in df[x][y].iterrows():
        o.append([row['Location'],row['Bin Number'],int(row['On Hand'])])
    return o

# #function used for pyautogui. Do not touch.
# def getShiftFromText(text):
#     """
#     Extract position from text copied in clipboard
#     """
#     locs=[];
#     ind1=text.find('Edit')
#     text=text[ind1::]
#     text=text.split('\n')
#     shift=0;
#     for line in text:
#         line=line.split('\t')
#         type=line[2]
#         if type=='Inventory Item':
#             return shift
#         shift+=1
#     return -1
#
#
# def getBinsFromText(text):
#     """
#     Extract bins from text copied in clipboard
#     """
#     locs=[];
#     ind1=text.find('BIN NUMBER')
#     if ind1==-1:
#         return []
#     text=text[ind1::]
#     ind1=text.find('AVAILABLE')
#     text=text[ind1::]
#     ind1=text.find('\t\n\t')
#     text=text[10:-18] #remove outside
#     text=text.split('\n')
#     for line in text:
#         line=line.split('\t')
#         location=line[2]
#         bin=line[0]
#         qty=line[3]
#         qty=qty.replace(' ','')
#         qty=qty.replace(',','')
#         if qty!='':
#             qty=int(qty)
#             locs.append([location,bin,qty])
#     return locs
#
#
# def getLocationsFromText(text):
#     """
#     Extract Locations from text copied in clipboard
#     """
#     locs=[];
#     ind1=text.find('CAE Warehouse')
#     ind2=text.find('\t\n\t')
#     text=text[ind1:ind2]
#     text=text.split('\n')
#     for line in text:
#         line=line.split('\t')
#         qty=line[1]
#         qty=qty.replace(' ','')
#         qty=qty.replace(',','')
#         if qty!='':
#             qty=int(qty)
#             locs.append([line[0],qty])
#     locs = sorted(locs, key=itemgetter(1),reverse=True)
#     return locs



#
#
# def lookPartInNetsuite(QCODE):
#     """
#     This function uses pyautogui to look for a particular QNERGY part number in netsuite.
#     Netsuite need to be open in a safari browse, maximized and zoomed out completely.
#     """
#     searchbarx=585
#     searchbary=67
#     viewx=49
#     viewy=210
#     idx=634
#     idy=133
#     invx=649
#     invy=509
#     backx=32
#     backy=138
#     WHERE={}
#     pyautogui.moveTo(searchbarx, searchbary, duration = 0.2)
#     time.sleep(0.2)
#     for i in range(5):
#         pyautogui.click(searchbarx, searchbary)
#         time.sleep(0.2)
#     pyautogui.hotkey('command', 'q') #its select all on azerty
#     time.sleep(0.1)
#     _workaround_write('"'+QCODE+'"') #input part name in search bar
#     time.sleep(0.1)
#     pyautogui.hotkey('enter') #enter
#     time.sleep(2)
#     pyautogui.moveTo(idx, idy-10, duration = 0.1)
#     time.sleep(0.2)
#     pyautogui.moveTo(idx+2, idy-10, duration = 0.3)
#     for i in range(3):
#         pyautogui.click(idx+2, idy-10)
#         time.sleep(0.1)
#     pyautogui.hotkey('command', 'q') #its select all on azerty
#     time.sleep(0.1)
#     pyautogui.hotkey('command', 'c')
#     time.sleep(0.1)
#     text=''
#     text=pyperclip.paste()
#     while len(text)==0:
#         for i in range(3):
#             pyautogui.click(idx+2, idy-10)
#             time.sleep(0.1)
#         pyautogui.hotkey('command', 'q') #its select all on azerty
#         time.sleep(0.1)
#         pyautogui.hotkey('command', 'c')
#         time.sleep(0.1)
#         text=pyperclip.paste()
#     if text.find('TOTAL')==-1:
#         print('no part')
#         pyautogui.moveTo(backx, backy, duration = 0.3)
#         for i in range(3):
#             pyautogui.click(backx, backy)
#             time.sleep(0.1)
#         return -1
#     R=text[text.find('TOTAL')+7]
#     #print(R)
#     if R=='1':
#         pyautogui.moveTo(viewx, viewy, duration = 0.1)
#         time.sleep(2)
#         pyautogui.click(viewx, viewy)
#     else:
#         shift=getShiftFromText(text) #shift should never be -1 normally
#         pyautogui.moveTo(viewx, viewy-15+15*shift, duration = 0.1)
#         time.sleep(2)
#         pyautogui.click(viewx, viewy-15+15*shift)
#     pyautogui.moveTo(invx, invy, duration = 0.1)
#     time.sleep(2.5)
#     for i in range(3):
#         pyautogui.click(invx, invy)
#         time.sleep(0.1)
#     pyautogui.moveTo(idx, idy, duration = 0.1)
#     time.sleep(2.5)
#     pyautogui.moveTo(idx+2, idy, duration = 0.3)
#     for i in range(3):
#         pyautogui.click(idx+2, idy)
#         time.sleep(0.1)
#     pyautogui.hotkey('command', 'q') #its select all on azerty
#     time.sleep(0.1)
#     pyautogui.hotkey('command', 'c')
#     time.sleep(0.1)
#     text=''
#     text=pyperclip.paste()
#     while len(text)<=1000:
#         for i in range(3):
#             pyautogui.click(idx+2, idy)
#             time.sleep(0.1)
#         pyautogui.hotkey('command', 'q') #its select all on azerty
#         time.sleep(0.1)
#         pyautogui.hotkey('command', 'c')
#         time.sleep(0.1)
#         text=pyperclip.paste()
#     return getBinsFromText(text)

#####Function to parse OctoSearch RESULTS

def ListAllOptions(mpn,QTY,lead):
    ih=IHI[mpn]
    print(lead+'    Available in house options :')
    if len(ih)==0:
        print(lead+color.RED+'        None'+color.END)
    else:
        for i in ih:
            start=color.GREEN
            if i[1]=='WESCO':
                start=color.YELLOW
            print(lead+start+'        %s available in %s (bin %s)'%(i[2],i[0],i[1])+color.END)
    #o=OctoI[mpn]
    o=getAllPricesfromResults(OctoSearches[mpn],QTY)
    #o=sorted(o, key=itemgetter(4),reverse=False)#Sort by priority
    print(lead+'    Available octopart options :')
    if len(o)==0:
        print(lead+color.RED+'        None'+color.END)
    else:
        c=0;
        for i in o:
            priority=i[4]
            start=color.RED
            if priority==0:
                start=color.GREEN
            elif priority==1:
                start=color.GREEN
            elif priority==2:
                start=color.YELLOW
            print(lead+start+"        Part %s made by %s : %s parts available at %s under SKU %s at price %s. Extended Price for %s parts = %s USD."%(i[1],i[0],i[6],i[2],i[5],i[8],i[7],i[9])+color.END)
            c+=1
            if c>5:
                break

def getLCSforPart(MPN,OctoSearches):
    try:
        x=OctoSearches[MPN]
    except:
        return '',"Unavailable"
    for spec in x.get("supSearchMpn",{}).get("results",{})[0].get("part").get("specs"):
        if spec.get("attribute").get("shortname")=="lifecyclestatus":
            if spec.get("displayValue")[0:3]=='Pro' or spec.get("displayValue")[0:3]=='New':
                return color.GREEN,spec.get("displayValue")
            elif spec.get("displayValue")[0:3] == 'NRN':
                return color.YELLOW,spec.get("displayValue")
            elif spec.get("displayValue")[0:3] == 'EOL' or spec.get("displayValue")[0:3] == 'Obs':
                return color.RED,spec.get("displayValue")
            else:
                return color.BLUE,spec.get("displayValue")
    return '',"Unavailable"


def resolve(mpn,QTY,IHI,OctoSearches,TIERLISTS):
    actions=[];
    remaining=QTY;
    try:
        ih=IHI[mpn]
    except:
        ih=[]
    total_price=0
    #Priority 0 use original we have in house
    #print(ih)
    if len(ih)>0:
        for i in ih:
            if i[1]!='WESCO':
                print(color.GREEN+'Use %s from %s (bin %s)'%(min(i[2],remaining),i[0],i[1])+color.END)
                actions.append('Use %s from %s (bin %s)\n'%(min(i[2],remaining),i[0],i[1]))
                col,stat=getLCSforPart(mpn,OctoSearches)
                print(col+'(%s life cycle status : %s)'%(mpn,stat)+color.END)
                actions.append('(%s life cycle status : %s)'%(mpn,stat))
                remaining-=min(i[2],remaining)
                if remaining==0:
                    return actions, remaining, total_price
    for sub in getSubs(mpn):
        #Priority 1 use substitutes we have in house
        try:
            ih=IHI[sub]
        except:
            ih=[]
        if len(ih)>0:
            for i in ih:
                if i[1]!='WESCO':
                    print(color.GREEN+'Use %s (substitute %s) from %s (bin %s)'%(min(i[2],remaining),sub,i[0],i[1])+color.END)
                    actions.append('Use %s (substitute %s) from %s (bin %s)\n'%(min(i[2],remaining),sub,i[0],i[1]))
                    col,stat=getLCSforPart(sub,OctoSearches)
                    print(col+'(%s life cycle status : %s)'%(sub,stat)+color.END)
                    actions.append('(%s life cycle status : %s)'%(sub,stat))
                    remaining-=min(i[2],remaining)
                    if remaining==0:
                        return actions, remaining, total_price
    #Priority 2 use original available in octopart for authorized and tier 1 sellers
    O=getBestPrice(mpn,remaining,0,OctoSearches,TIERLISTS)
    if len(O)>0:
        for o in O[2]:
            actions.append('Order %s %s from %s : $%s\n'%(o[2],o[1],o[0],o[3]))
            print(color.GREEN+'Order %s %s from %s : $%s'%(o[2],o[1],o[0],o[3])+color.END)
            col,stat=getLCSforPart(mpn,OctoSearches)
            print(col+'(%s life cycle status : %s)'%(mpn,stat)+color.END)
            actions.append('(%s life cycle status : %s)'%(mpn,stat))
        remaining-=min(O[0],remaining)
        total_price+=O[1]
        if remaining==0:
            return actions, remaining, total_price
    #Priority 3 use substitue available in octopart for authorized and tier 1 sellers
    for sub in getSubs(mpn):
        O=getBestPrice(sub,remaining,0,OctoSearches,TIERLISTS)
        if len(O)>0:
            for o in O[2]:
                actions.append('Order %s %s (substitute %s) from %s : $%s\n'%(o[2],o[1],sub,o[0],o[3]))
                print(color.GREEN+'Order %s %s (substitute %s) from %s : $%s'%(o[2],o[1],sub,o[0],o[3])+color.END)
                col,stat=getLCSforPart(sub,OctoSearches)
                print(col+'(%s life cycle status : %s)'%(sub,stat)+color.END)
                actions.append('(%s life cycle status : %s)'%(sub,stat))
            remaining-=min(O[0],remaining)
            total_price+=O[1]
            if remaining==0:
                return actions, remaining, total_price
    #Priority 4 use original available in octopart for tier 2 sellers
    O=getBestPrice(mpn,remaining,1,OctoSearches,TIERLISTS)
    if len(O)>0:
        for o in O[2]:
            actions.append('Order %s %s from %s : $%s\n'%(o[2],o[1],o[0],o[3]))
            print(color.YELLOW+'Order %s %s from %s : $%s'%(o[2],o[1],o[0],o[3])+color.END)
            col,stat=getLCSforPart(mpn,OctoSearches)
            print(col+'(%s life cycle status : %s)'%(mpn,stat)+color.END)
            actions.append('(%s life cycle status : %s)'%(mpn,stat))
        remaining-=min(O[0],remaining)
        total_price+=O[1]
        if remaining==0:
            return actions, remaining, total_price
    #Priority 5 use substitue available in octopart for tier 2 sellers
    for sub in getSubs(mpn):
        O=getBestPrice(sub,remaining,1,OctoSearches,TIERLISTS)
        if len(O)>0:
            for o in O[2]:
                actions.append('Order %s %s (substitute %s) from %s : $%s\n'%(o[2],o[1],sub,o[0],o[3]))
                print(color.YELLOW+'Order %s %s (substitute %s) from %s : $%s'%(o[2],o[1],sub,o[0],o[3])+color.END)
                col,stat=getLCSforPart(sub,OctoSearches)
                print(col+'(%s life cycle status : %s)'%(sub,stat)+color.END)
                actions.append('(%s life cycle status : %s)'%(sub,stat))
            remaining-=min(O[0],remaining)
            total_price+=O[1]
            if remaining==0:
                return actions, remaining, total_price
    #priority 6 : get it back from wesco
    if len(ih)>0:
        for i in ih:
            if i[1]=='WESCO':
                print(color.YELLOW+'Use %s from %s (bin %s)'%(min(i[2],remaining),i[0],i[1])+color.END)
                actions.append('Use %s from %s (bin %s)\n'%(min(i[2],remaining),i[0],i[1]))
                col,stat=getLCSforPart(mpn,OctoSearches)
                print(col+'(%s life cycle status : %s)'%(mpn,stat)+color.END)
                actions.append('(%s life cycle status : %s)'%(mpn,stat))
                remaining-=min(i[2],remaining)
                if remaining==0:
                    return actions, remaining, total_price
    #Priority 7 substitutes from wesco
    for sub in getSubs(mpn):
        ih=IHI[sub]
        if len(ih)>0:
            for i in ih:
                if i[1]=='WESCO':
                    actions.append('Use %s (substitute %s) from %s (bin %s)\n'%(min(i[2],remaining),sub,i[0],i[1]))
                    print(color.YELLOW+'Use %s (substitute %s) from %s (bin %s)'%(min(i[2],remaining),sub,i[0],i[1])+color.END)
                    col,stat=getLCSforPart(sub,OctoSearches)
                    print(col+'(%s life cycle status : %s)'%(sub,stat)+color.END)
                    actions.append('(%s life cycle status : %s)'%(sub,stat))
                    remaining-=min(i[2],remaining)
                    if remaining==0:
                        return actions, remaining, total_price
    #Priority 8 use original available in octopart for tier 3
    O=getBestPrice(mpn,remaining,2,OctoSearches,TIERLISTS)
    if len(O)>0:
        for o in O[2]:
            actions.append('Order %s %s from %s : $%s\n'%(o[2],o[1],o[0],o[3]))
            print(color.RED+'Order %s %s from %s : $%s'%(o[2],o[1],o[0],o[3])+color.END)
            col,stat=getLCSforPart(mpn,OctoSearches)
            print(col+'(%s life cycle status : %s)'%(mpn,stat)+color.END)
            actions.append('(%s life cycle status : %s)'%(mpn,stat))
        remaining-=min(O[0],remaining)
        total_price+=O[1]
        if remaining==0:
            return actions, remaining, total_price
    #Priority 8 use substitue available in octopart for tier 3
    for sub in getSubs(mpn):
        O=getBestPrice(sub,remaining,2,OctoSearches,TIERLISTS)
        if len(O)>0:
            for o in O[2]:
                actions.append('Order %s %s (substitute %s) from %s : $%s'%(o[2],o[1],sub,o[0],o[3]))
                print(color.RED+'Order %s %s (substitute %s) from %s : $%s'%(o[2],o[1],sub,o[0],o[3])+color.END)
                col,stat=getLCSforPart(sub,OctoSearches)
                print(col+'(%s life cycle status : %s)'%(sub,stat)+color.END)
                actions.append('(%s life cycle status : %s)'%(sub,stat))
            remaining-=min(O[0],remaining)
            total_price+=O[1]
            if remaining==0:
                return actions, remaining, total_price
    if remaining>0:
        print(color.RED+'Find %s parts elsewhere.'%(remaining)+color.END)
        actions.append('Find %s parts elsewhere.\n'%(remaining))
    return actions, remaining, total_price






def getBestPrice(MPN,QTY,PRIORITY,OctoSearches,TIERLISTS):
    O=[]
    try:
        x=OctoSearches[MPN]
    except:
        return []
    o=getAllPricesfromResults(OctoSearches[MPN],QTY,TIERLISTS)
    for j in range(len(o)):
        o=getAllPricesfromResults(OctoSearches[MPN],QTY,TIERLISTS)
        i=j
        remaining=QTY
        total_parts=0
        total_price=0
        actions=[]
        while i < len(o) and remaining > 0 :
            if o[i][4]==PRIORITY:
                quantity=o[i][7]
                if quantity>0:
                    price=o[i][9]
                    supplier=o[i][2]
                    sku=o[i][5]
                    actions.append([supplier,sku,quantity,price])
                    remaining-=min(quantity,remaining)
                    total_parts+=quantity
                    total_price+=price
                    o=getAllPricesfromResults(OctoSearches[MPN],remaining,TIERLISTS)
            i+=1
        #if total_parts>=QTY:
        missing=max(QTY-total_parts,0)
        O.append([total_parts,total_price,actions,missing])
    #print(O)
    if len(O)>0:
        O = sorted(O, key=itemgetter(1)) #by Price
        O = sorted(O, key=itemgetter(3)) #by quantity
        return O[0]
    return []


def getAllPricesfromResults(results,qty,TIERLISTS):
    allprices=[];
    if results and results.get("supSearchMpn",{}).get("hits",{})!=0:
        for it in results.get("supSearchMpn",{}).get("results",{}):
            part=it.get("part",{})
            prices=getBestPriceForPart(part,qty,TIERLISTS)
            allprices=allprices+prices;
        allprices = sorted(allprices, key=itemgetter(4),reverse=False) #this is sorted by priority
    return allprices

def getBestPriceForPart(part,required_qty,TIERLISTS):
    sellers=part.get("sellers",{})
    pricing=[];
    for seller in sellers:
        #print(seller.get('company').get('name'))
        bestofferprice=getBestPriceFromSeller(seller,required_qty,TIERLISTS)
        if len(bestofferprice)>0:
            pricing.append([part.get("manufacturer",{}).get("name"),part.get("mpn")]+bestofferprice)
    if len(pricing)>0:
        pricing = sorted(pricing, key=itemgetter(9),reverse=False)
        return pricing
    else:
        return []

def getBestPriceFromSeller(seller,required_qty,TIERLISTS):
    ##test seller here
    priority=rankSeller(seller,TIERLISTS) #0 is highest
    offers=seller.get("offers",{})
    pricing=[];
    for offer in offers:
        bestofferprice=getBestPriceFromOffer(offer,required_qty)
        if len(bestofferprice)>0:
            pricing.append(bestofferprice)
    if len(pricing)>0:
        pricing = sorted(pricing, key=itemgetter(4),reverse=False)
        return [seller.get('company').get('name'),seller.get('company').get('id'),priority]+pricing[0]
    else:
        return []

def getBestPriceFromOffer(offer,required_qty):
    prices=offer.get('prices',{})
    moq=offer.get('moq',{})
    inventoryLevel=offer.get('inventoryLevel',{})
    #print(prices)
    if type(inventoryLevel)==type(1) and inventoryLevel<required_qty:
        if inventoryLevel<=0:
            return []
        required_qty=inventoryLevel
    if type(moq)==type(1) and required_qty<moq:
        required_qty=moq
    if type(moq)==type(1) and type(inventoryLevel)==type(1) and inventoryLevel<moq:
        return []
    pricing=[];
    for price in prices:
        if price.get('currency')=='USD' and price.get('quantity')<=inventoryLevel:
            extended_price=max(required_qty,price.get('quantity'))*price.get('price')
            pricing.append([max(required_qty,price.get('quantity')),extended_price/max(required_qty,price.get('quantity')),extended_price])
    if len(pricing)>0:
        pricing = sorted(pricing, key=itemgetter(2),reverse=False)
        return [offer.get('sku',{}),offer.get('inventoryLevel',{})]+pricing[0]
    else:
        return []

def rankSeller(seller,TIERLISTS):
    isAuthorized=seller.get("isAuthorized")
    id=seller.get("company",{}).get("id")
    #print(id)
    if isAuthorized:
        return 0
    tier=1
    for TIERLIST in TIERLISTS:
        if int(id) in TIERLIST:
            return tier
        tier+=1
    return tier


#######Functions for name matching (needed when supplied name for suppliers doesnt match exactly the name on octopart)
def wordMatchScore(str1,str2):
    l1=len(str1)
    l2=len(str2)
    r1=str1.lower()*l2
    r2=str2.lower()*l1
    s=0.00001;
    for i in range(l1):
        for j in range(l2):
            v=0.2
            if (i+1<l1 and j+1<l2):
                v+=0.4*float(r1[(i+1)+(j+1)*l1]==r2[(i+1)*l2+(j+1)])
            if (i-1>=0 and j-1>=0):
                v+=0.4*float(r1[(i-1)+(j-1)*l1]==r2[(i-1)*l2+(j-1)])
            s+=v*float(r1[i+j*l1]==r2[i*l2+j]);
    return s

def normalizedWordMatchScore(str1,str2):
    return wordMatchScore(str1,str2)/np.sqrt(wordMatchScore(str1,str1)*wordMatchScore(str2,str2))#/((0.2+(0.5*min(l1,l2)+0.5*max(l1,l2)))-1)

def sentenceMatchScore(str1,str2):
    str1=str1.replace('.',' ')
    str2=str2.replace('.',' ')
    w1s=str1.split(' ')
    w2s=str2.split(' ')
    w1ss=[];
    w2ss=[];
    w1scores=[]
    for w1 in w1s:
        matches = re.findall("[a-z][A-Z]",w1)
        ind1=0
        for match in matches:
            ind=w1.find(match)+1
            w1ss.append(w1[ind1:ind])
            ind1=ind
        w1ss.append(w1[ind1::])
    for w2 in w2s:
        matches = re.findall("[a-z][A-Z]",w2)
        ind1=0
        for match in matches:
            ind=w2.find(match)+1
            w2ss.append(w2[ind1:ind])
            ind1=ind
        w2ss.append(w2[ind1::])
    score=1;
    for w1 in w1ss:
        bestscore=0;
        for w2 in w2ss:
            newscore=normalizedWordMatchScore(w1,w2)
            if newscore>bestscore:
                bestscore=newscore
        w1scores.append(bestscore)
    w1scores.sort(reverse=True)
    for i in range(min(len(w1ss),len(w2ss))):
        score*=w1scores[i]
    return score

def scoreList(str1,strlist,idlist):
    RESULTS=[];
    for i in range(len(strlist)):
        score1=sentenceMatchScore(str1,strlist[i])
        score2=sentenceMatchScore(str1.replace(' ','').lower(),strlist[i].replace(' ','').lower())
        RESULTS.append([strlist[i],max(score1,score2),idlist[i]])
    return RESULTS

def getSellerOctoUID(LISTQ):
    print('Looking for preferred sellers IDs on octopart.')
    #looks for match from list1 into list2 and list3 if no match in list2.
    STID1=[];
    issues=[];
    for request in LISTQ:
        scores=scoreList(request,SELLERS,SELLERSID)
        scores = sorted(scores, key=itemgetter(1),reverse=True)
        requestSolved=False
        if scores[0][1]==1:
            i=0
            requestSolved=True
            while (scores[i][1]==1):
                print('Found ID %s for %s as %s.'%(scores[i][2],request,scores[i][0]))
                STID1.append(scores[i][2]);
                i+=1
        else:
            print('Exact seller name %s not found in list.'%(request))
            i=0;
            while (scores[i][1]>0.8):
                print('Possible Match : %s (%s match score)'%(scores[i][0],scores[i][1]))
                x=input('Include ? (y/n) ')
                if x.lower()=='y':
                    STID1.append(scores[i][2]);
                    requestSolved=True
                i+=1
        if requestSolved==False:
            print('No seller ID found for %s.'%(request))
            print('Would you like to look up %s in manufacturers ? '%(request))
            x=input('Include ? (y/n) ')
            if x.lower()=='y':
                scores=scoreList(request,MANUFACTURERS,MANUFACTURERSID)
                scores = sorted(scores, key=itemgetter(1),reverse=True)
                if scores[0][1]==1:
                    i=0
                    requestSolved=True
                    while (scores[i][1]==1):
                        print('Found ID %s for %s as %s.'%(scores[i][2],request,scores[i][0]))
                        STID1.append(scores[i][2]);
                        i+=1
                else:
                    print('Exact manufacturer name %s not found in list.'%(request))
                    i=0;
                    while (scores[i][1]>0.8):
                        print('Possible Match : %s (%s match score)'%(scores[i][0],scores[i][1]))
                        x=input('Include ? (y/n) ')
                        if x.lower()=='y':
                            STID1.append(scores[i][2]);
                            requestSolved=True
                        i+=1
                if requestSolved==False:
                    print('Seller %s has no ID on octopart.'%(request))
                    issues.append(request)
    if len(issues)==0:
        print('All sellers have been identified.')
    else:
        print('The following sellers have not been found :')
        for seller in issues:
            print(seller)
    return [*set(STID1)]



#As found at https://octopart.com/api/v4/values#attributes
df = pd.read_csv('data/allSuppliers.csv',encoding = "ISO-8859-1",sep=';',keep_default_na=False)
SELLERS=[];
SELLERSID=[];
for i in df.index:
    SELLERS.append(df.loc[i]['Name']);
    SELLERSID.append(df.loc[i]['ID']);

df = pd.read_csv('data/allManufacturers.csv',encoding = "ISO-8859-1",sep=';',keep_default_na=False)
MANUFACTURERS=[];
MANUFACTURERSID=[];

for i in df.index:
    MANUFACTURERS.append(df.loc[i]['Name']);
    MANUFACTURERSID.append(df.loc[i]['ID']);

df = pd.read_csv('data/supplierTier1.txt',header=None)
ST1=[]
for i in df.index:
    ST1.append(df.loc[i][0]);

df = pd.read_csv('data/supplierTier2.txt',header=None)
ST2=[]
for i in df.index:
    ST2.append(df.loc[i][0]);




#####Function to make reports
def makeNewReport(REQ,IHI,OctoSearches,TIERLISTS,filename):
    f = open(filename, "w")
    print('Search Report :')
    f.write('Search Report :\n')
    bill=0
    issues=[];
    for i in range(len(REQ)):
        print('----------------------------------------')
        f.write('----------------------------------------\n')
        MPN=REQ[i]['MPN']
        QTY=REQ[i]['QTY']
        print('Resolving part '+color.BOLD+MPN+color.END+' (required qty : '+color.BOLD+str(QTY)+color.END+')')
        f.write('Resolving part '+MPN+' (required qty : '+str(QTY)+')\n')
        a,remaining,totalprice=resolve(MPN,QTY,IHI,OctoSearches,TIERLISTS)
        for action in a:
            f.write(action)
        bill+=totalprice
        if remaining>0:
            issues.append([MPN,remaining,QTY])
    print('----------------------------------------')
    f.write('----------------------------------------\n')
    print('Total = $%s'%(bill))
    f.write('Total = $%s\n'%(bill))
    print('----------------------------------------')
    f.write('----------------------------------------\n')
    print('Remaining  issues :')
    f.write('Remaining  issues :\n')
    if len(issues)>0:
        for issue in issues:
            print(color.RED+'Still need to find %s/%s parts for component %s'%(issue[1],issue[2],issue[0])+color.END)
            f.write('Still need to find %s/%s parts for component %s\n'%(issue[1],issue[2],issue[0]))
    else:
        print('None')
        f.write('None\n')
    f.close()
