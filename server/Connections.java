import java.util.*;
import java.io.*;

/**
 * This class acts as a wrapper for whatever data structure holds the list of
 * output streams which connect the clients
 * @author David Fraser
 */

public class Connections {

    private Hashtable<String,DataOutputStream> data = new Hashtable<String,DataOutputStream>();
    
    /** Adds a connection to the list of connections
     * @param username The username of the person connection
     * @param stream The output stream of the connection the user connected on
     */

    public void add(String username,DataOutputStream stream) {
        data.put(username,stream);
    }
    
    /** Removes a connection from the list of connections
     * @param username The username of the connection to be removed
     */
    
    public void remove(String username) {
        data.remove(username);
    }
    
    /** Returns a stream which is associated with that username if it exists
     * @param username The username of the connection to retrieve
     * @return Returns the output stream for that username, if it doesnt exist
     * returns null
     */
    
    public DataOutputStream retrieve(String username) {
        return data.get(username);
    }

    /** Checks to see if a username exists and if there is a refrence to it in
     * the structure
     * @param username The username you wish to check
     * @return True if it does exist, false otherwise
     */

    public boolean check(String username) {
        return data.containsKey(username);
    }

}
    
