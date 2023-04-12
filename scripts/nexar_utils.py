
#credentials to access Nexar API
clientId = '16a2d2c4-be09-4b77-9e9a-3510baf81df6';
clientSecret = 'f47c6321-96f4-436b-961e-b35d84b0d6a8';

nexar = NexarClient(clientId, clientSecret)

#needs export og global variables
os.environ['NEXAR_CLIENT_ID'] = clientId
os.environ['NEXAR_CLIENT_SECRET'] = clientSecret
os.environ['NEXAR_STORAGE_PATH'] = 'cache_dir' #make sure this folder exists


CUSTOM_QUERY = '''query Search($mpn: String!){
  supSearchMpn(
    country:"US"
    currency:"USD"
    q: $mpn
    inStockOnly: true
    limit: 30
  ) {
    hits
    results {
      description
      part {
        mpn
         specs{
         attribute{
            shortname
          }
          displayValue
        }
        manufacturer {
          name
          id
        }
        totalAvail
        sellers {
          company {
            name
            id
          }
          offers{
            sku
            inventoryLevel
            moq
            eligibleRegion
            prices{
			  price
          	  currency
          	  quantity
              convertedPrice
            }
          }
          country
          isAuthorized
        }
      }
    }
  }
}
'''
