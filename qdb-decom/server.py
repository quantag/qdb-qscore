from flask import Flask, request, jsonify
import base64

app = Flask(__name__)

@app.route('/dec', methods=['POST'])
def dec():
    data = request.json
    print(data)
    decodedSrc = base64.b64decode(data['src'])
    print(decodedSrc)
    loc = {}
    exec(decodedSrc, globals(), loc)
    result = loc['code777']
    print( result )
    return jsonify( {'res':result} )

if __name__ == '__main__':
    app.run(debug=True)