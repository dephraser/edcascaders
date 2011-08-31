import java.io.*;
import java.net.*;
import java.util.*;

/**
 * @author David Fraser
 */

public class Server {

    //Need to store the connections some how
    
    private Connections connections = new Connections();

    /**
     * Constructor says what port to listen on
     * @param  port  What port the server will listen on
     */

    public Server( int port ) throws IOException {

        //All we have to do is listen
        System.out.println("Spinning the server up, stand by...");
        listen(port);
    }

    /**
     * Listens on the port and creates a thread for each new connection comming
     * in
     * @param port What port to listen on
     */

    public listen( int port ) throws IOException {

        //Make the server socket
        ss = new ServerSocket(port);
        System.out.println("Server started, listening on port "+port);

        //Start accepting connections indefinitly

        while(true) {

            //Grab the incoming connection
            Socket s = ss.accept();
            System.out.println("Connection from " + s);

            //Create a new output stream for sending data back to the client
            
            DataOutputStream 
