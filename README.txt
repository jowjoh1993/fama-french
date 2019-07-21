#-------------------------------------------------------------------------------------#
# Implementation of Fama-French 3-Factor Model to inform equity investment decisions  #
# Author: 	Joshua W. Johnstone                                                       #
#-------------------------------------------------------------------------------------#

### Introduction ###

The goal of this project is to take a practical approach to investing using the Fama-French
three-factor model. This model is an extension to the familiar CAPM, which explains returns
as a linear function of excess return of the market portfolio over the risk-free rate. The
Fama-French model (FF) introduces two new independent factors: SMB, and HML.



### "Quick"-start guide ###

This assumes you have (free) Quandl and TD Ameritrade developer accounts, and you know how to create
and refresh your access token for the TD account. If you do not know how to do this, please
see "Using the TD Ameritrade developer API" below.

1. Download the project and unzip if necessary to a location of your choice

2. Open the folder "TDA" (for "TD Ameritrade")

	a. In the file "client_id.txt", copy and paste the Consumer Key of your TD developer app.
	   The consumer key should be the ONLY thing in this file. Save the file.
	b. In your browser, refresh your TDA access token. I have not gotten this to work from 
	   a local Python program yet. Your token expires 30 minutes after you refresh it, as of
	   the time of this writing. https://developer.tdameritrade.com/authentication/apis/post/token-0
	c. In the file "access_token.txt", copy and paste your fresh access token, and save the file.
	   The access token should be the ONLY thing in this file.

3. In the file "quandl_authtoken.txt", copy and paste the auth token for your Quandl account. 
   The token should be the ONLY thing in this file. Save the file.
   
4. In the file "asset_universe.txt", list out the ticker symbols of stocks you want to include
   in the analysis, one symbol per line, all upper case. Include at least a few hundred tickers
   to make sure there's enough data for the model.
   
5. Open up the Python script "fama_french.py" in your favorite Python IDE (I use Spyder). 

	a. Ensure that you have installed all the modules in the "Import Modules" section
	b. Change the value of the "root_dir" variable to the location you put the project. For example,
	   if "fama_french.py" is in C:\Users\tonystark\Desktop, set root_dir=r"C:\Users\tonystark\Desktop".
	   The "r" before the quotes is necessary to prevent Python from reading escape characters.
	
6. Run the Python script cell-by-cell
	
	Note that there is a time sleep of 0.3 seconds in between each of the API requests to TD. This
	is because TD has a request limit of 2 per second. An asset universe of 2500 stocks will take 
	about 20 minutes to make all the requests. Since the access token only lasts 30 minutes, you will
	have to stop in the middle of the program (between requests for fundamental data and price data)
	and refresh the token. 
	
	   

### The Model ###

The model takes the following form:

R_j - R_f = alpha_j + beta1_j*(R_m - R_f) + beta2_j*(R_smb) + beta3_j*(R_hml)

where

R_j	: The return of stock j
R_f	: The risk-free rate of return
R_m	: The return of the market portfolio
alpha_j : How much the stock outperforms after returns explained by the three factors
R_smb	: Excess return of small cap stocks over large cap stocks
R_hml	: Excess return of value stocks over growth stocks
beta1	: Sensitivity of stock j to excess market returns
beta2	: Sensitivity of stock j to R_smb
beta3	: Sensitivity of stock j to R_hml

The goal is to fit the model for each stock in our asset universe. In other words, given R_j, R_f,
R_m, R_smb, and R_hml, we can use linear regression to calculate alpha_j, beta1_j, beta1_j, and
beta3_j. Ideally, this provides us with a way to predict the future returns of stock j. If the model
fits well, then a higher alpha indicates that a stock provides a better reward than is expected
based on its risk.



### The Three Factors ###

# Excess Market Return #
Excess Market Return (Rm - Rf), present in the CAPM, is the difference in returns between a portfolio
representative of the market as a whole, and the risk-free rate. In this project, the market
portfolio was constructed as the sum of the NASDAQ ("NDX"), the NYSE ("NYA"), and the Arca
Major Market Index ("XMI"). The 1-year US Treasury bill was used for the risk-free rate.

# SMB #
SMB (Small Minus Big) is the excess return of stocks of companies with small market capitalization
over stocks of companies with large market capitalization. Small cap stocks tend to outperform
large cap stocks, and the FF intends to capture this tendency with the SMB factor. It is 
calculated by building hypothetical portfolios of large and small cap stocks, calculating
returns, and taking the difference in returns.

# HML #
HML (High Minus Low) is the excess return of stocks of companies with high book-to-market (BM)
ratios (known as value stocks) over stocks of companies with low BM ratios (growth stocks).
Value stocks tend to outperform growth stocks, and the FF captures this tendency with the HML
factor. It is calculated by building hypothetical portfolios of high and low BM ratios, calculating
returns, and taking the difference in returns.

For further information on the calculation of the SMB and HML factors, see French's article here:
http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_developed.html



### Asset universe ###

The asset universe describes which stocks are considered in the analysis. For this implementation, 
the universe consists of all 505 stocks in the S&P 500, and all roughly 2000 stocks in the Russell 
2000.

Note that you will need at least a few hundred stocks in your asset universe to ensure that you
have at least one stock in each of the six FF portfolios.


### Data collection ###

The US T-bill rates were obtained from Quandl. You will need to make a free account with them in 
order to pull data using their API, and make sure you have the quandl Python module installed and
imported. In Python:

tbill = quandl.get("USTREASURY/BILLRATES", authtoken="<your quandl account auth token>")

All fundamental data (data about the companies themselves, used to calculate the HML and SMB factors)
and all pricing data was collected using the TD Ameritrade developer API. 

You can create a developer account with TD Ameritrade for free, but their API was not designed with the
beginner in mind. As a new API user myself, it was quite challenging to figure out how to successfully
authenticate and request data from a local Python program. I will do my best to describe the steps here.



### Using the TD Ameritrade developer API ###

This monster was not designed to be easy to use. It's not too bad once you get it set up, but it takes
some tricky (and not obvious) steps to get there. 

Much of the credit for these steps goes to the u/carlos85333, who created this Reddit post:
https://www.reddit.com/r/algotrading/comments/914q22/successful_access_to_td_ameritrade_api/

I will mostly be recounting those steps here, with some additional detail.



1. Go to https://developer.tdameritrade.com/ and click "Register" to create an account.

2. You need to create an app to use the API. Go to "My Apps" and create a new app

3. Fill in the details. Give it any name you want, but set the Callback URL to http:\\localhost\<name_of_your_app>
   For example, if you named the app "tdapp", set Callback URL = http:\\localhost\tdapp
   (If you understand networking concepts better than I do, feel free to change this)
   
4. Once the App is created, view it by going to My Apps. Save off the following information:

	Consumer Key: This is the same thing as client_id, or the user id for the app. This is what you will 
		be pasting into <root_dir>\TDA\client_id.txt.
		
	Callback URL: Find this by clicking on the "Details" tab. This is the same thing as redirect_uri.
	
5. Encode the Callback URL. 

	Go to https://meyerweb.com/eric/tools/dencoder/ , paste the Callback URL into the box, click "Encode",
	and copy the output to a text file. This is your Encoded Callback URL.
	
6. In Windows search, go to "Turn Windows features on or off." Make sure that the following two boxes are
   checked:
   
	Internet Information Services
	Internet Information Services Hostable Web Core
	
7. Obtain an authorization code. You need this code to get an access token, which you need to authenticate
   requests from a local program.
   
	a. Paste the following into your browser's address bar:
	
		https://auth.tdameritrade.com/auth?response_type=code&redirect_uri=<EncodedCallbackURL>&client_id=<ConsumerKey>
		
	   Replace <EncodedCallbackURL> with the output you saved from step 5.
	   Replace <ConsumerKey> with the consumer key from step 4.
	   
	b. Hit enter. If successful, you will be taken to a page where you can authenticate your app using your
	   username and password. Do this now.
	   
	c. Once this is complete, you will be taken to a webpage that gives you a 404 Not Found error. This is fine.
       Look again in your browser's address bar. Somewhere in the URL, you should see the following:
	   
		...&code=<long_complicated_code>&...
		
	   You need to copy <long_complicated_code> and paste it into a text file.
	   
8. Decode <long_complicated_code>. Go back to https://meyerweb.com/eric/tools/dencoder/ , paste in the
   <long_complicated_code>, hit "Decode", and copy-paste the output into a text file. Let's call this
   output <decoded_code>.
   
9. Obtain an access_token and a refresh_token.

	a. In the browser, go to https://developer.tdameritrade.com/authentication/apis/post/token-0
	b. Fill in the following information:
	
		grant_type 		= authorization_code
		refresh_token 	= <empty>
		access_type 	= offline
		code 			= <decoded_code>
		client_id 		= <ConsumerKey>
		redirect_uri 	= <EncodedCallbackURL>
		
	c. Click "Send." You should receive a response containing the following:
		
		access_token (valid for the next 30 minutes)
		refresh_token (valid forever, used to get a new access_token)
		
	d. Paste access_token into the file <root_dir>\TDA\access_token.txt and save the file.
	e. Paste refresh_token into any file you like and save it.
	
	You should now be good to go. To see if it works, test it by going to 
		
	https://developer.tdameritrade.com/quotes/apis/get/marketdata/quotes
	
	Set 
		symbol 			= GOOG
		authorization 	= Bearer <access_token>
	
	and hit send. You should get a response 200 with data for GOOG.



## Refreshing your access_token ##

1. Go to https://developer.tdameritrade.com/authentication/apis/post/token-0

2. Set the following fields (note refresh_token is literally the text "refresh_token", but 
   <refresh_token> is your actual refresh token that you saved off):

	grant_type		= refresh_token
	refresh_token 	= <refresh_token>
	client_id		= <ConsumerKey>
	
3. Hit Send, then copy-paste the new access token into <root_dir>\TDA\access_token.txt

You can leave the browser tab open and the fields populated, so all you need to do to refresh
is push Send and copy-paste the new access token.