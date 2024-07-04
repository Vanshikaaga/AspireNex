import requests
from bs4 import BeautifulSoup
import argparse
import os
import pandas as pd
from flask import Flask, render_template, send_from_directory, request
from PIL import Image
from io import BytesIO

app = Flask(__name__)

# Argument parsing setup
parser = argparse.ArgumentParser()
parser.add_argument('--saveto', help='Target directory to save the images (default: static/images/)', dest='dirName')
parser.add_argument('--pages', help='Number of pages (default: 40)', dest='last_pagination')
args = parser.parse_args()

# Default values for directory name and number of pages
dirName = args.dirName or 'static/images/'
last_pagination = int(args.last_pagination) + 1 if args.last_pagination else 40

# Create target directory if it doesn't exist
if not os.path.exists(dirName):
    os.makedirs(dirName)

# Function to fetch image URLs, names, prices, descriptions, and ratings from a search query
def fetch_product_details(link, last_pagination):
    urls = [link + '&page=' + str(x) for x in range(1, last_pagination)]
    product_data = []

    headers_std = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
        'Content-Type': 'text/html',
    }

    for pag, url in enumerate(urls, start=1):
        print(f'Pagination: {pag}, URL: {url}')
        req = requests.get(url, headers=headers_std).text
        soup = BeautifulSoup(req, 'html.parser')
        products = soup.find_all('div', {'class': 's-result-item'})
        
        for k, product in enumerate(products, start=1):
            img_tag = product.find('img', {'class': 's-image'})
            name_tag = product.find('span', {'class': 'a-size-medium a-color-base a-text-normal'})
            price_tag = product.find('span', {'class': 'a-price-whole'})
            desc_tag = product.find('span', {'class': 'a-text-normal'})
            rating_tag = product.find('span', {'class': 'a-icon-alt'})
            
            if img_tag and 'src' in img_tag.attrs:
                img_url = img_tag['src']
                img_filename = f'{pag}_{k}.jpg'
                name = name_tag.text.strip() if name_tag else 'N/A'
                price = price_tag.text.strip() if price_tag else 'N/A'
                description = desc_tag.text.strip() if desc_tag else 'N/A'
                rating = rating_tag.text.strip() if rating_tag else 'N/A'
                
                product_data.append({
                    'url': img_url,
                    'filename': img_filename,
                    'name': name,
                    'price': price,
                    'description': description,
                    'rating': rating
                })
                print(f'Image URL: {img_url}, Name: {name}, Price: {price}, Description: {description}, Rating: {rating}')

                # Download image
                response = requests.get(img_url)
                img = Image.open(BytesIO(response.content))

                # Save image to file
                img_path = os.path.join(dirName, img_filename)
                img.save(img_path)
                print(f'Saved Image: {img_path}')

    return product_data

# Flask route to display the index page with images
@app.route('/')
def index():
    images = os.listdir(dirName)
    
    try:
        df = pd.read_csv('data.csv')
        product_data = df.to_dict(orient='records')
    except FileNotFoundError:
        product_data = None
    
    return render_template('index.html', images=images, product_data=product_data)

# Flask route to serve images from 'static/images/'
@app.route('/images/<filename>')
def display_image(filename):
    return send_from_directory('static/images', filename)

# Flask route to handle product comparison form submission
@app.route('/compare', methods=['POST'])
def compare_products():
    selected_images = request.form.get('selected_images')
    
    if not selected_images:
        return "No images selected for comparison. Please select exactly two images."

    selected_images = selected_images.split(',')

    if len(selected_images) != 2:
        return "Please select exactly two images to compare."

    print(f"Selected Image Filenames for Comparison: {selected_images}")  # Debugging log

    try:
        df = pd.read_csv('data.csv')
    except FileNotFoundError:
        return "Data file not found. Please run the scraping script first."

    # Retrieve data based on filename
    selected_data = df[df['filename'].isin(selected_images)]

    if len(selected_data) != 2:
        return "Selected products not found in data."

    product1_data = selected_data.iloc[0]
    product2_data = selected_data.iloc[1]

    return render_template('compare.html', product1=product1_data, product2=product2_data)

if __name__ == '__main__':
    # User input for search query URL and category
    link = input('Search Query URL: ')
    item_category = input('Enter the search category: ')

    # Fetching product details from the search query
    product_data = fetch_product_details(link, last_pagination)

    # Prepare DataFrame for URLs, filenames, names, prices, descriptions, ratings, and categories
    categories = [item_category] * len(product_data)
    df2 = pd.DataFrame(product_data)
    df2['category'] = categories

    print(f'New DataFrame: {df2}')

    # Concatenate both DataFrames and save to CSV
    try:
        df1 = pd.read_csv('data.csv')
        print(f'Existing DataFrame: {df1}')
    except FileNotFoundError:
        df1 = pd.DataFrame(columns=['url', 'filename', 'name', 'price', 'description', 'rating', 'category'])
        print(f'Creating new DataFrame')

    df = pd.concat([df1, df2], ignore_index=True)
    df.to_csv('data.csv', index=False)
    print(f'Saved DataFrame to CSV: {df}')
    print(f'Initial length: {len(df1)}')
    print(f'New length: {len(df2)}')
    print(f'Total length: {len(df)}')
    app.run(debug=True)