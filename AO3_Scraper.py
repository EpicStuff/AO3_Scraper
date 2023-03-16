import requests, time, csv, re, sys, os
from bs4 import BeautifulSoup
from tqdm import tqdm
from requests.exceptions import RequestException
from colorama import init, Fore


def main(password=''):
	# Starting message
	print('Welcome to AO3 Bookmark Scraper')
	print('You can scrape public bookmarks of any user, or scrape your private bookmarks if you log in\n')

	# logging in and getting username
	while True:
		while True:
			username = input('username : ')
			# if not a valid username, continue
			if not re.match(r'^[\w\d._-]+$', username): print('Invalid input: Please enter a valid username'); continue
			# ask for password
			try: password = input('password (Ctrl + c to skip login): ')
			except KeyboardInterrupt: print(''); break

			session = requests.Session()
			try:
				# Make a GET request to the login page
				r = session.get('https://archiveofourown.org/users/login')

				# Parse the HTML content of the page
				soup = BeautifulSoup(r.content, 'html.parser')

				# Find the authenticity token in the page source code
				token = soup.find('input', {'name': 'authenticity_token'})
				if token is None:
					# If the authenticity token is not found, print an error message
					print('\nAuthenticity token not found. Please check the page source code.')
				else:
					# If the authenticity token is found, get the value of the token
					token = token['value']

			except requests.exceptions.RequestException as e:
				# Handle exceptions that may occur during the GET request
				print(f'\nAn error occurred while making the GET request: {e}')

			# Creates payload to login to ao3
			payload = {'utf8': '✓', 'authenticity_token': token, 'user[login]': username, 'user[password]': password, 'commit': 'Log in'}
			try:
				# POST request to ao3 to login
				p = session.post('https://archiveofourown.org/users/login', data=payload)
			except requests.exceptions.RequestException as e:
				# Handle exceptions that may occur during the POST request
				print(f'An error occurred while making the POST request: {e}')
				continue  # If the POST request fails, ask the user to enter the credentials again

			# Check if the response indicates a successful login
			if 'Successfully logged in' in p.text:
				# Login successful
				print(Fore.GREEN, '   Login successful', Fore.RESET)
				break  # If the login is successful, break out of the loop
			else:
				# Login failed
				print(Fore.RED, '   Login failed', Fore.RESET)
			continue  # If the login is not successful, ask the user to enter the credentials again

		print('Scraping bookmarks of: ' + Fore.BLUE + username + Fore.RESET)

		# Check if the username exists
		try:
			response = requests.get(f'https://archiveofourown.org/users/{username}')
			response.raise_for_status()
			soup = BeautifulSoup(response.text, 'html.parser')
			# If the username exists, break out of the loop
			if len(soup.find_all('div', class_='user')) > 0: break
			else:
				# If the username does not exist, print an error message
				print(f'Username {username} does not exist')
				# If the username does not exist, ask the user to enter a valid username
				print('Please enter a valid username')

		# Handle exceptions that may occur during the GET request
		except RequestException as e:
			print('Error connecting to the server. Please check your internet connection and try again')

	# Create base URL for the user's AO3 bookmarks
	base_url = f'https://archiveofourown.org/users/{username}/bookmarks?page='

	# Initialize page2 to a default value
	page2 = None

	# Get the number of pages of bookmarks available
	while True:
		try:
			# If the user logged in, make a GET request to the user's bookmarks page private=true
			if password: response = session.get(f'{base_url}?private=true')
			# If the user did not log in, make a GET request to the user's bookmarks page
			else: response = requests.get(base_url)
			response.raise_for_status()
			soup = BeautifulSoup(response.text, 'html.parser')
			bookmarks = soup.find_all('li', class_='bookmark')
			if len(bookmarks) == 0: print('User ' + Fore.BLUE + '{username}' + Fore.RESET + ' has no bookmarks'); return  # if user has no bookmarks
			pagination = soup.find('ol', class_='actions')
			if pagination is not None:
				pagination = pagination.find_all('li')
				last_page = int(pagination[-2].text)
			else:
				last_page = 1

			print(f'{Fore.BLUE}{last_page}{Fore.RESET} pages of bookmarks available')
			break
		except requests.exceptions.HTTPError as e:
			print(f'Error connecting to the server: {e}')
		except (AttributeError, ValueError):
			print('Error parsing the HTML: pagination element not found')
			break

	while True:
		try:
			# Get the starting page number to scrape from
			page1 = int(input('start page: '))
			if page1 < 1: print('Invalid input: Please enter a valid number'); continue
			try:
				if password: response = session.get(f'{base_url}{page1}?private=true')
				else: response = requests.get(f'{base_url}{page1}')
				response.raise_for_status()
				soup = BeautifulSoup(response.text, 'html.parser')
				bookmarks = soup.find_all('li', class_='bookmark')
				if len(bookmarks) == 0:
					print('Start page is out of range')
					continue
			except ValueError:
				print('Invalid input: Please enter a valid number')
				continue
			except RequestException as e:
				print('Error connecting to the server. Please check your internet connection and try again')
				continue
			while True:
				try:
					# Get the ending page number to scrape to
					page2 = int(input('stop page: '))
					if page2 < 1:
						print('Invalid input: Please enter a valid number')
						continue
					if page1 > page2:
						print('Invalid input: End page should be bigger or equal to start page')
						continue
					try:
						if password: response = session.get(f'{base_url}{page2}?private=true')
						else: response = requests.get(f'{base_url}{page2}')
						response.raise_for_status()
						soup = BeautifulSoup(response.text, 'html.parser')
						bookmarks = soup.find_all('li', class_='bookmark')
						if len(bookmarks) == 0:
							print('End page is out of range')
							continue
					except ValueError:
						print('Invalid input: Please enter a valid number')
					except RequestException as e:
						print('Error connecting to the server. Please check your internet connection and try again')
						continue
					break
				except ValueError:
					print('Invalid input: Please enter a valid number')
			break
		# Handle any errors that may occur
		except ValueError:
			print('Invalid input: Please enter a valid number')

	while True:
		try:
			# Prompt for delay
			print('Consider longer delays if you are scraping a large number of pages')
			delay = int(input('delay (in seconds): '))
			# Check if the input is valid
			if delay < 0: raise ValueError
			break
		# Handle any errors that may occur
		except ValueError:
			print('Invalid input: enter a non negative number')

	# Open a CSV file for writing
	with open(username + '_ao3_bookmarks.csv', 'w', newline='', encoding='utf-8') as csvfile:
		# Create a CSV writer object
		csvwriter = csv.writer(csvfile)
		# Write the header row
		csvwriter.writerow(
			['URL', 'Title', 'Authors', 'Fandoms', 'Warnings', 'Rating', 'Categories', 'Characters', 'Relationships',
				'Tags', 'Words', 'Date Bookmarked', 'Date Updated', 'Bookmarker\'s Notes', 'Bookmarker\'s Tags'])

		# Calculate the total number of pages to scrape
		total_pages = page2 - page1 + 1

		# Use tqdm to create a progress bar with the total number of pages to scrape
		for page in tqdm(range(page1, page2 + 1), total=total_pages, desc='Scraping'):
			start_time = time.time()
			try:
				# Send a GET request to the current page
				if password: response = session.get(f'{base_url}{page}?private=true')
				else: response = requests.get(f'{base_url}{page}')
				time.sleep(delay)  # Add delay between requests to be respectful to the website
				soup = BeautifulSoup(response.text, 'html.parser')  # Parse the HTML of the page using BeautifulSoup
			except requests.exceptions.RequestException as e:
				print('Error: ', e)
				break

			# Extract the data using the provided selectors
			for bookmark in soup.select('li.bookmark'):
				title_element = bookmark.select_one('h4 a:nth-of-type(1)')
				if title_element:
					title = title_element.text
				# Skip the bookmark if it doesn't have a title
				else:
					continue

				if title:
					# Extract the data using the provided selectors
					authors = bookmark.select('a[rel=\'author\']')
					fandoms = bookmark.select('.fandoms a')
					warnings = bookmark.select('li.warnings')
					rating = bookmark.select_one('span.rating')
					categories = bookmark.select('span.category')
					words = bookmark.select_one('dd.words') or bookmark.select_one('dd')
					tags = bookmark.select('li.freeforms')
					characters = bookmark.select('li.characters')
					relationships = bookmark.select('li.relationships')
					date_bookmarked = bookmark.select_one('div.user p.datetime')
					url = bookmark.select_one('h4 a:nth-of-type(1)')['href']
					date_updated = bookmark.select_one('p.datetime')
					bookmarkers_notes = bookmark.select_one('.userstuff.notes')
					bookmarkers_tags = bookmark.select_one('.meta.tags.commas')

					# Check if the bookmark has authors
					authors.element = bookmark.select('a[rel=\'author\']')
					if authors.element:
						authors = [author.text for author in authors]
						if authors:
							authors = ' ' + authors[0] + '; ' + '; '.join(authors[1:])
					else:
						authors = ''

					# Check if the bookmark has fandoms
					fandoms.element = bookmark.select('.fandoms a')
					if fandoms.element:
						fandoms = [fandom.text for fandom in fandoms]
						if fandoms:
							fandoms = ' ' + fandoms[0] + '; ' + '; '.join(fandoms[1:])
					else:
						fandoms = ''

					# Check if the bookmark has warnings
					warnings_element = bookmark.select('span.warnings')
					if warnings_element:
						warnings = [warning.text for warning in warnings_element]
						if warnings:
							warnings = ' ' + warnings[0] + '; ' + '; '.join(warnings[1:])
					else:
						warnings = ''

					# Check if the bookmark has a rating
					rating.element = bookmark.select('span.rating')
					if rating.element:
						rating = [rating.text for rating in rating.element]
						if rating:
							rating = ' ' + rating[0] + '; ' + '; '.join(rating[1:])
					else:
						rating = ''

					# Check if the bookmark has categories
					categories.element = bookmark.select('span.category')
					if categories.element:
						categories = [category.text for category in categories.element]
						if categories:
							categories = ' ' + categories[0] + '; ' + '; '.join(categories[1:])
					else:
						categories = ''

					tags_element = bookmark.select('li.freeforms')
					if tags_element:
						tags = [tag.text for tag in tags_element]
						if tags:
							tags = ' ' + tags[0] + '; ' + '; '.join(tags[1:])
					else:
						tags = ''

					# Check if the bookmark has characters
					characters_element = bookmark.select('li.characters')
					if characters_element:
						characters = [character.text for character in characters_element]
						if characters:
							characters = ' ' + characters[0] + '; ' + '; '.join(characters[1:])
					else:
						characters = ''

					# Check if the bookmark has relationships
					relationships_element = bookmark.select('li.relationships')
					if relationships_element:
						relationships = [relationship.text for relationship in relationships_element]
						if relationships:
							relationships = ' ' + relationships[0] + '; ' + '; '.join(relationships[1:])
					else:
						relationships = ''

					# Check if the bookmark has a date
					date_bookmarked = date_bookmarked.text if date_bookmarked else ''

					# Check if the bookmark has a word count
					words = words.text if words else ''

					# Check if the bookmark has a URL
					url = 'https://archiveofourown.org' + url if url else ''

					# Check if the bookmark has a date updated
					date_updated = date_updated.text if date_updated else ''

					bookmarkers_notes = bookmarkers_notes.text.strip('\n') if bookmarkers_notes else ''

					bookmarkers_tags = ', '.join(bookmarkers_tags.text.strip('\n').split('\n')) if bookmarkers_tags else ''

					# Write the data to the CSV file
					csvwriter.writerow([url, title, authors, fandoms, warnings, rating, categories, characters, relationships, tags, words, date_bookmarked, date_updated, bookmarkers_notes, bookmarkers_tags])
			from requests.exceptions import RequestException

			try:
				# Send a GET request to the current page
				if password: response = session.get(f'{base_url}{page}?private=true', timeout=60)
				else: response = requests.get(f'{base_url}{page}', timeout=60)
			except RequestException as e:
				print(f'Error loading page {page}. {e}')
				print('Please try again later.')
				print('If the problem persists, consider longer delay times between requests.')
				break

	# Message at the end of the program
	print('All done!')
	print('Your bookmarks have been saved to ' + Fore.BLUE + username + Fore.RESET + '_ao3_bookmarks.csv')


if __name__ == '__main__':
	main()
	os.system('pause')
	sys.exit()
