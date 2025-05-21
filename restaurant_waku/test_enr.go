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
        PreferGo: false, // Use Go's DNS resolver instead of the system's
        Dial: func(ctx context.Context, network, address string) (net.Conn, error) {
            // Dial 192.168.1.26:53 for DNS queries
            d := net.Dialer{
                Timeout: 20 * time.Second, // Set a timeout for DNS queries
            }
            conn, err := d.DialContext(ctx, "udp", "192.168.1.26:53")
            fmt.Println("RET:", conn)
            return conn, err
        },
    }

    client := dnsdisc.NewClient(dnsdisc.Config{Resolver: resolver})

    domain, pubkey, err := dnsdisc.ParseURL("enrtree://ANXEZXZA6FE7C56VORF77F2ZLCD72U3QST4XD27EWBOSXVKLIDLRC@nodes.restaurants.com") //enrtree://AOGYWMBYOUIMOENHXCHILPKY3ZRFEULMFI4DOM442QSZ73TT2A7VI@test.waku.nodes.status.im
    if err != nil {
        fmt.Println("Error resolving enrtree:", err)
        return
    }
    fmt.Println("domain:", domain)
    fmt.Println("pubkey:", pubkey)
          
/*    txts, err := client.cfg.Resolver.LookupTXT("FDXN3SN67NA5DKA4J2GOK7BVQI.nodes.restaurants.com")
    fmt.Println("txts:", txts)
*/                                          //AOGYWMBYOUIMOENHXCHILPKY3ZRFEULMFI4DOM442QSZ73TT2A7VI
    tree, err := client.SyncTree("enrtree://ANXEZXZA6FE7C56VORF77F2ZLCD72U3QST4XD27EWBOSXVKLIDLRC@nodes.restaurants.com") //enrtree://AOGYWMBYOUIMOENHXCHILPKY3ZRFEULMFI4DOM442QSZ73TT2A7VI@test.waku.nodes.status.im
    if err != nil {
        fmt.Println("Error syncing enrtree:", err)
        return
    }
    fmt.Println("tree:", tree.ToTXT("nodes.restaurants.com"))

/*    for _, enr := range nodes {
        fmt.Println("Resolved ENR:", enr.String())
    }
*/}