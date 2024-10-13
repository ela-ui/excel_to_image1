import streamlit as st
import pandas as pd
import os
import shutil
from pathlib import Path
import re

# Custom CSS for background color and text styles
st.markdown(
    """
    <style>
        body {
            background-color: black;
            color: white;
        }
        .stButton>button {
            background-color: #FF6F61;
            color: white;
            border-radius: 10px;
            font-size: 16px;
        }
        .stTextInput>div>input {
            color: white;
            background-color: #333;
        }
        .stTextInput>label {
            color: #FF6F61;
        }
        .stSpinner {
            color: #FF6F61;
        }
        .stMarkdown {
            color: #FF6F61;  /* Stylish color for markdown text */
        }
    </style>
    """,
    unsafe_allow_html=True
)


# Function to read client IDs from Excel
def read_client_ids_from_excel(excel_path):
    try:
        df = pd.read_excel(excel_path)
        if 'ClientID' not in df.columns:
            raise ValueError("Excel file must contain a 'ClientID' column.")
        df['ClientID'] = df['ClientID'].astype(str).str.zfill(11)
        return df, set(df['ClientID'])
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return pd.DataFrame(), set()

# Function to extract the number from the filename
def extract_number_from_filename(file_name):
    match = re.match(r'(\d+)', file_name.split('_')[0])
    if match:
        return match.group(1).zfill(11)
    return None

# Function to match images with client IDs and store them in the output folder
def match_images_with_client_ids(client_ids, images_dir, output_folder):
    # Ensure the images directory exists
    if not os.path.exists(images_dir):
        st.error(f"The directory {images_dir} does not exist. Please check the path.")
        return [], [], {}

    # Create output folder if it doesn't exist
    output_folder_path = Path(output_folder)
    output_folder_path.mkdir(parents=True, exist_ok=True)  # Create the folder if necessary

    matched_images = []
    mismatched_images = []
    matched_image_count = {client_id: 0 for client_id in client_ids}

    # Iterate through files in the image directory
    for file_name in os.listdir(images_dir):
        file_path = os.path.join(images_dir, file_name)
        if os.path.isfile(file_path):  # Ensure it's a file
            number = extract_number_from_filename(file_name)
            if number in client_ids:
                matched_images.append(file_name)
                shutil.copy(file_path, output_folder_path)  # Copy matched image to output folder
                matched_image_count[number] += 1
            else:
                mismatched_images.append(file_name)

    return matched_images, mismatched_images, matched_image_count

# Function to update Excel file with the match status
def update_excel_with_status(excel_df, matched_image_count, output_excel_path):
    excel_df['Matched Images Count'] = excel_df['ClientID'].apply(
        lambda x: matched_image_count.get(x, 0)
    )
    excel_df['Status'] = excel_df['ClientID'].apply(
        lambda x: 'Matched' if matched_image_count.get(x, 0) > 0 else 'Mismatched'
    )
    excel_df.to_excel(output_excel_path, index=False)
    st.success(f"Updated Excel file saved at {output_excel_path}")

# Main image processing function
def process_images(excel_path, images_dir, output_folder, fallback_images_dir=None):
    excel_df, client_ids = read_client_ids_from_excel(excel_path)
    if excel_df.empty or not client_ids:
        st.error("No valid client IDs found.")
        return

    # Match images in primary directory
    matched_images, mismatched_images, matched_image_count = match_images_with_client_ids(client_ids, images_dir, output_folder)
    unmatched_client_ids = {cid for cid in client_ids if matched_image_count[cid] == 0}

    # Process fallback directory if unmatched IDs exist and fallback path is provided
    if unmatched_client_ids and fallback_images_dir:
        st.write("Processing fallback directory for unmatched client IDs...")
        fallback_matched_images, fallback_mismatched_images, fallback_matched_image_count = match_images_with_client_ids(
            unmatched_client_ids, fallback_images_dir, output_folder
        )
        for cid, count in fallback_matched_image_count.items():
            matched_image_count[cid] += count

    # Update the Excel file with the status
    updated_excel_path = excel_path.replace('.xlsx', '_updated.xlsx')
    update_excel_with_status(excel_df, matched_image_count, updated_excel_path)

    st.write(f"Matched and copied {len(matched_images)} images from the primary directory.")
    st.write(f"Total mismatched images: {len(mismatched_images)}")
    st.write(f"Total matched images: {sum(matched_image_count.values())}")

    return updated_excel_path

# Streamlit app UI
def main():
    st.title("Image Matching Automation Tool")

    # File path inputs
    excel_path = st.text_input("Enter the path to the Excel file")
    images_dir = st.text_input("Enter the path to the Primary Images Directory")
    output_folder = st.text_input("Enter the path to the Output Folder for Matched Images")
    fallback_images_dir = st.text_input("Enter the path to the Fallback Images Directory (optional)", "")

    # Process button
    if st.button("Process Images"):
        if excel_path and images_dir and output_folder:
            with st.spinner("Processing..."):
                # Call the main processing function
                updated_excel_path = process_images(excel_path, images_dir, output_folder, fallback_images_dir)
                
                if updated_excel_path:
                    # Provide download link for updated Excel file
                    with open(updated_excel_path, "rb") as file:
                        btn = st.download_button(
                            label="Download Updated Excel File",
                            data=file,
                            file_name=os.path.basename(updated_excel_path),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
        else:
            st.error("Please provide all required inputs.")

if __name__ == "__main__":
    main()
