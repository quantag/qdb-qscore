from flask import Flask, request, jsonify
import base64
import logging
import datetime

app = Flask(__name__)
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/dec', methods=['POST'])
def dec():
    try:
        data = request.json
        decodedSrc = base64.b64decode(data['src'])
        logging.info(f"Incoming script: {decodedSrc.decode()}")

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        script_filename = f"scripts/script{timestamp}.py"
        with open(script_filename, 'w') as f:
            f.write(decodedSrc.decode())

        loc = {}
        exec(decodedSrc, globals(), loc)
        result = loc.get('code777')
        if result is not None:
            encoded_result = base64.b64encode(str(result).encode()).decode()
            logging.info(f"Execution result: {result}")
            return jsonify({'status':0,'res': encoded_result})
        else:
            logging.error('Expected result was not found')
            return jsonify({'status':1,'err':'Expected result was not found'})
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return jsonify({'status':2,'err': str(e)})

if __name__ == '__main__':
    app.run(debug=True)