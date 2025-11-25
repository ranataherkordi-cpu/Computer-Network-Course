import http.server
import socketserver
import json
import threading
import cmd
import http.client

PORT = 5000
HOST = "localhost"

# In-memory storage for users
users = {}

class Handler(http.server.SimpleHTTPRequestHandler):
    
    def _set_response(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.end_headers()
    
    def do_POST(self):
        if self.path == '/register':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            # Validate input
            if 'user_id' not in data or 'ip' not in data or 'port' not in data:
                self._set_response(400)
                self.wfile.write(json.dumps({'status': 'error', 'message': 'Missing required fields'}).encode('utf-8'))
                return

            user_id = data['user_id']
            ip = data['ip']
            port = data['port']

            # Check for duplicate user_id
            if user_id in users:
                self._set_response(409)
                self.wfile.write(json.dumps({'status': 'error', 'message': 'Username already exists'}).encode('utf-8'))
                return

            users[user_id] = {'ip': ip, 'port': port}

            self._set_response(201)
            self.wfile.write(json.dumps({'status': 'registered'}).encode('utf-8'))

    def do_GET(self):
        if self.path == '/peers':
            peers = list(users.keys())
            if not peers:
                self._set_response(404)
                self.wfile.write(json.dumps({'status': 'error', 'message': 'No users registered yet'}).encode('utf-8'))
                return
            self._set_response()
            self.wfile.write(json.dumps({'peers': peers}).encode('utf-8'))

        elif self.path.startswith('/peerinfo'):
            query = self.path.split('?')[-1]
            username = query.split('=')[-1]
            if not username:
                self._set_response(400)
                self.wfile.write(json.dumps({'status': 'error', 'message': 'Missing username parameter'}).encode('utf-8'))
                return

            if username not in users:
                self._set_response(404)
                self.wfile.write(json.dumps({'status': 'error', 'message': 'User not found'}).encode('utf-8'))
                return

            user_info = users[username]

            self._set_response()
            self.wfile.write(json.dumps({'user_info': user_info}).encode('utf-8'))

# Start the server in a separate thread
def start_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()

class P2PChatCLI(cmd.Cmd):
    prompt = '> '
    intro = "Welcome to the P2P Chat CLI. Type help or ? to list commands.\n"

    def do_menu(self, arg):
        'Show the main menu: menu'
        self.print_menu()

    def print_menu(self):
        menu = """
        Main Menu:
        1. Register a new user by command : (register user_id ip port)
        2. List all registered peers by command : (peers)
        3. Get information about a peer by command : (peerinfo user_id)
        4. Exit
        """
        print(menu)
    
    def do_register(self, arg):
        'Register a new user: register user_id ip port'
        try:
            user_id, ip, port = arg.split()
            conn = http.client.HTTPConnection(HOST, PORT)
            payload = json.dumps({
                "user_id": user_id,
                "ip": ip,
                "port": port
            })
            headers = {
                'Content-Type': 'application/json'
            }
            conn.request("POST", "/register", payload, headers)
            response = conn.getresponse()
            data = response.read().decode()
            conn.close()
            
            result = json.loads(data)
            if response.status == 201:
                print("User registered successfully")
            else:
                print(f"Error: {result['message']}")
        except ValueError:
            print("Invalid arguments. Usage: register user_id ip port")
        except Exception as e:
            print(f"Error: {e}")
    
    def do_peers(self, arg):
        'List all registered peers: peers'
        try:
            conn = http.client.HTTPConnection(HOST, PORT)
            conn.request("GET", "/peers")
            response = conn.getresponse()
            data = response.read().decode()
            conn.close()
            
            if response.status == 200:
                result = json.loads(data)
                for user_id in result['peers']:
                    print(user_id)
            else:
                result = json.loads(data)
                print(f"Error: {result['message']}")
        except Exception as e:
            print(f"Error: {e}")
    
    def do_peerinfo(self, arg):
        'Get information about a peer: peerinfo user_id'
        if not arg:
            print("Missing username parameter")
            return
        
        try:
            conn = http.client.HTTPConnection(HOST, PORT)
            conn.request("GET", f"/peerinfo?username={arg}")
            response = conn.getresponse()
            data = response.read().decode()
            conn.close()
            
            if response.status == 200:
                result = json.loads(data)
                user_info = result['user_info']
                print(f"IP: {user_info['ip']}\nPort: {user_info['port']}")
            else:
                result = json.loads(data)
                print(f"Error: {result['message']}")
        except Exception as e:
            print(f"Error: {e}")
    
    def do_exit(self, arg):
        'Exit the CLI: exit'
        print("Goodbye!")
        return True

if __name__ == '__main__':
    # Start the server
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()

    # Start the CLI
    cli = P2PChatCLI()
    cli.print_menu()
    cli.cmdloop()
