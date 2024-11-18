from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify, flash
import os
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24) 

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xls', 'xlsx'}

#  upload folder exits
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Load Excel file and validate columns
def load_and_validate_excel(file_path, required_columns):
    try:
        df = pd.read_excel(file_path)
        if not all(column in df.columns for column in required_columns):
            return None, f"Missing required columns: {required_columns}"
        return df, None
    except Exception as e:
        return None, str(e)

# Route: Main Page
@app.route('/')
def index():
    step = request.args.get('step', 'upload_referral')
    return render_template('index.html', step=step)

# Route: Upload Referral Fee File
@app.route('/upload_referral', methods=['POST'])
def upload_referral_file():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        file_path = os.path.join(UPLOAD_FOLDER, 'referral_fees.xlsx')
        file.save(file_path)
        flash('Referral Fee file uploaded successfully', 'success')
        return redirect(url_for('index', step='upload_cost'))
    flash('Invalid file format', 'error')
    return redirect(url_for('index'))

# Route: Upload Product Cost File and Process Data
@app.route('/upload_cost', methods=['POST'])
def upload_cost_file():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        product_file_path = os.path.join(UPLOAD_FOLDER, 'product_costs.xlsx')
        file.save(product_file_path)

        referral_file_path = os.path.join(UPLOAD_FOLDER, 'referral_fees.xlsx')
        if not os.path.exists(referral_file_path):
            flash('Referral Fee file is missing. Please upload it first.', 'error')
            return redirect(url_for('index', step='upload_referral'))

        # Load and validate files
        cost_df, error = load_and_validate_excel(product_file_path, ['Product Name', 'Cost'])
        if error:
            flash(error, 'error')
            return redirect(url_for('index', step='upload_cost'))
        referral_df, error = load_and_validate_excel(referral_file_path, ['Product Name', 'Referral Fee'])
        if error:
            flash(error, 'error')
            return redirect(url_for('index', step='upload_referral'))

        # Merge and process data
        merged_df = pd.merge(cost_df, referral_df, on='Product Name', how='inner')
        merged_df['Total Cost'] = merged_df['Cost'] * merged_df['Referral Fee']

        # Save processed file
        processed_file_path = os.path.join(UPLOAD_FOLDER, 'processed_data.xlsx')
        merged_df.to_excel(processed_file_path, index=False)

        flash('Product Cost file uploaded and processed successfully', 'success')
        return redirect(url_for('processed_data'))
    flash('Invalid file format', 'error')
    return redirect(url_for('index'))

# Route: Processed Data Page
@app.route('/processed_data')
def processed_data():
    processed_file_path = os.path.join(UPLOAD_FOLDER, 'processed_data.xlsx')
    if os.path.exists(processed_file_path):
        return render_template('processed_data.html', file_path='processed_data.xlsx')
    flash('No processed data found. Please upload files again.', 'error')
    return redirect(url_for('index'))

# Route: Download Processed File
@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    flash('File not found', 'error')
    return redirect(url_for('processed_data'))

# Route: User Data with Visualization
@app.route('/user_data')
def user_data():
    processed_file_path = os.path.join(UPLOAD_FOLDER, 'processed_data.xlsx')
    if os.path.exists(processed_file_path):
        df = pd.read_excel(processed_file_path)
        total_sales = df['Total Cost'].sum()
        product_sales = df.groupby('Product Name')['Total Cost'].sum().to_dict()
        return render_template('user_data.html', total_sales=total_sales, product_sales=product_sales)
    return 'No processed data found.', 400


if __name__ == '__main__':
    app.run(debug=True)
