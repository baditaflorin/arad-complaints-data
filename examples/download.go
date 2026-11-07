// go run examples/download.go [JSON_URL] [OUTPUT_PATH]
// Standard library only; Go 1.18+.
package main

import (
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "os"
    "time"
)

func run() error {
    url := "https://baditaflorin.github.io/arad-complaints-data/data/records.json"
    output := "records.json"
    if len(os.Args) > 1 { url = os.Args[1] }
    if len(os.Args) > 2 { output = os.Args[2] }
    client := &http.Client{Timeout: 60 * time.Second}
    req, err := http.NewRequest(http.MethodGet, url, nil)
    if err != nil { return err }
    req.Header.Set("User-Agent", "AradDataExample/1.0")
    req.Header.Set("Accept", "application/json")
    response, err := client.Do(req)
    if err != nil { return err }
    defer response.Body.Close()
    if response.StatusCode != http.StatusOK { return fmt.Errorf("HTTP %d", response.StatusCode) }
    const maxBytes = 64 << 20
    payload, err := io.ReadAll(io.LimitReader(response.Body, maxBytes + 1))
    if err != nil { return err }
    if len(payload) > maxBytes { return fmt.Errorf("response exceeds 64 MiB") }
    var records []map[string]interface{}
    if err = json.Unmarshal(payload, &records); err != nil { return err }
    if records == nil { return fmt.Errorf("expected a JSON array") }
    if err = os.WriteFile(output, payload, 0644); err != nil { return err }
    fmt.Printf("%d records saved to %s\n", len(records), output)
    return nil
}

func main() { if err := run(); err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) } }
