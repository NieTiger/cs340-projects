import socket


HOST = "127.0.0.1"
PORT = 8765

backlog = 8

with socket.socket() as server_socket:
    # tell the kernel to reuse sockets that are in "TIME_WAIT" state
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(8)
    print(f"Listening on http://{HOST}:{PORT}")

    # Listen on the socket forever
    while True:
        # Get client socket and address
        client_sock, client_addr = server_socket.accept()

        # Read everything from the sock
