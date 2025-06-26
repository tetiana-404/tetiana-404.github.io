import json
import boto3.dynamodb
import pandas as pd
import boto3
from botocore.exceptions import ClientError

def get_object_from_s3_bucket(bucket_name, file_key):
   
    s3_client = boto3.client('s3')

    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        file_content = response.get('Body').read().decode('utf-8')
        json_data = json.loads(file_content)
    except Exception:
        print("Error in getting the object from the bucket")
        return None

    return json_data

def import_data_from_json(object):
   
    return pd.DataFrame(object)

def drop_unnecessary_columns(df, columns_to_drop: list):
   
    for column in columns_to_drop:
        df.drop(column, axis=1, inplace=True)
    
    return df

def reorder_columns_in_data(df, columns_order: list):

    return df[columns_order]

def language_transformation(df, lang_dict: dict):
    """
    this function substitutes full language names with their code in ISO 639-1 format
    :param df: pandas DF or dict of data
    :param lang_dict: dictionary with language codes in ISO 639-1 format
    :return: pandas dataframe or dict of data with replaced languages
    """
    #replace_language = lambda x: lang_dict.get(x, x)

    df_copy = df.copy()
    df_copy['language'] = df_copy['language'].apply(lambda x: replace_language(x, lang_dict))
    
    return df_copy

def replace_language(lang: str, lang_dict: dict):
    
    lang_list = lang.split(',')
    new_lang = ""
    for i in range(len(lang_list) - 1):
        new_lang = new_lang + lang_dict[lang_list[i].strip()] + ', '
    
    new_lang = new_lang + lang_dict[lang_list[-1].strip()]
    return new_lang

def year_transformation(df):
   
    transform_year = lambda x: f"{str(abs(int(x)))} BC" if int(x) <= 0 else f"{x} AD"

    df_copy = df.copy()
    df_copy['year'] = df_copy['year'].astype(str)
    df_copy['year'] = df_copy['year'].apply(transform_year)
    return df_copy

def load_data_to_dynamo_db_table(df):
    """
    this function loads data to DynamoDB table from dataframe or dictionary
    :param df: dataframe or dict of data to load to DynamoDB table
    :return: status: e.g. 200 - Success
    """
    dynamodb = boto3.resource('dynamodb')
    try:
        table = dynamodb.Table('100_best_books')
    except ClientError as e:
        return -1
    
    for index, row in df.iterrows():
        item = {
            "author": row['author'],
            "title": row['title'],
            "year": row['year'],
            "language": row['language'],
            "pages": row['pages']
        }
        table.put_item(Item=item)
    return 200

def lambda_handler(event, context):
    bucket_name = event['Records'][0]['s3']['bucket']['name'] 
    file_key_books= event['Records'][0]['s3']['object']['key']
    file_key_language= 'language.json'

    columns_to_drop = ["country", "imageLink", "link"] # TODO: write here which columns you need to drop
    columns_order = [ "author", "title", "year", "language", "pages"] # TODO: write here appropriate order of columns

    object_books = get_object_from_s3_bucket(bucket_name, file_key_books)
    object_language = get_object_from_s3_bucket(bucket_name, file_key_language)

    initial_df_books = import_data_from_json(object_books)
    
    analyzed_df_books = drop_unnecessary_columns(initial_df_books, columns_to_drop)

    analyzed_df_books = reorder_columns_in_data(analyzed_df_books, columns_order)
    
    # load language codes from JSON object
    # TODO: write your code here to load language codes to dictionary
    lang_dict = object_language # this dictionary you will receive as a result of your upload

    analyzed_df_books = language_transformation(analyzed_df_books, lang_dict)
    
    analyzed_df_books = year_transformation(analyzed_df_books)
    print(analyzed_df_books)

    result = load_data_to_dynamo_db_table(analyzed_df_books)
    return result