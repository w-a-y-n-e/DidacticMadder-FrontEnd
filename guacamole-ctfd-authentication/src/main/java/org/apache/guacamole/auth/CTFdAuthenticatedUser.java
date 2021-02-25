package org.apache.guacamole.auth;
import org.apache.guacamole.net.auth.AbstractAuthenticatedUser;
import org.apache.guacamole.net.auth.AuthenticationProvider;
import org.apache.guacamole.net.auth.Credentials;
import org.apache.guacamole.auth.CTFdAuthenticationProvider;

/**
 * An HTTP header implementation of AuthenticatedUser, associating a
 * username and particular set of credentials with the HTTP authentication
 * provider.
 */
public class CTFdAuthenticatedUser extends AbstractAuthenticatedUser {

    /**
     * Reference to the authentication provider associated with this
     * authenticated user.
     */
    private AuthenticationProvider authProvider = new CTFdAuthenticationProvider();

    /**
     * The credentials provided when this user was authenticated.
     */
    private Credentials credentials;

    /**
     * Initializes this AuthenticatedUser using the given username and
     * credentials.
     *
     * @param username
     *     The username of the user that was authenticated.
     *
     * @param credentials
     *     The credentials provided when this user was authenticated.
     */
    public void init(String username, Credentials credentials) {
        this.credentials = credentials;
        setIdentifier(username.toLowerCase());
    }

    @Override
    public AuthenticationProvider getAuthenticationProvider() {
        return authProvider;
    }

    @Override
    public Credentials getCredentials() {
        return credentials;
    }

}
