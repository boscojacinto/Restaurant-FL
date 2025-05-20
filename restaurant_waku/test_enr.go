package main

import (
    "fmt"
    "net"
    "time"
    "context"
    "github.com/ethereum/go-ethereum/p2p/dnsdisc"
)

func main() {
    fmt.Println("hello")

    resolver := &net.Resolver{
        PreferGo: true, // Use Go's DNS resolver instead of the system's
        Dial: func(ctx context.Context, network, address string) (net.Conn, error) {
            // Dial 127.0.0.1:53 for DNS queries
            d := net.Dialer{
                Timeout: 5 * time.Second, // Set a timeout for DNS queries
            }
            return d.DialContext(ctx, "udp", "127.0.0.1:53")
        },
    }

    client := dnsdisc.NewClient(dnsdisc.Config{Resolver: resolver})

    // enrtree://AKRU4HIYKQMOAKI73MNOTUNKKFH7VNX4TAQU7ULDGK5MNX5EDDSRU@nodes.restaurants.com
    domain, pubkey, err := dnsdisc.ParseURL("enrtree://ALDB6VZEW72YNBC4JWUYN3Y2BD3REXRXN7E22IHOU7UUTDB3JJNWU@nodes.restaurants.com")
    if err != nil {
        fmt.Println("Error resolving enrtree:", err)
        return
    }
    fmt.Println("domain:", domain)
    fmt.Println("pubkey:", pubkey)

    tree, err := client.SyncTree("enrtree://ALDB6VZEW72YNBC4JWUYN3Y2BD3REXRXN7E22IHOU7UUTDB3JJNWU@nodes.restaurants.com")
    if err != nil {
        fmt.Println("Error syncing enrtree:", err)
        return
    }
    fmt.Println("tree:", tree)

/*    for _, enr := range nodes {
        fmt.Println("Resolved ENR:", enr.String())
    }
*/}