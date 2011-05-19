// server.go - compiler server
// 
// Copyright 2011 Ashley Hewson
// 
// This file is part of Compiler Zoo.
// 
// Compiler Zoo is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// Compiler Zoo is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with Compiler Zoo.  If not, see <http://www.gnu.org/licenses/>.

package main

import (
    "log"
    "io"
    "io/ioutil"
    "http"
    "strings"
    "os"
    "json"
)

type DriverResult struct {
    Success bool
    Result string
}

func RunDriver(driver, source string) DriverResult {
    inR, inW, inE := os.Pipe()
    outR, outW, outE := os.Pipe()

    if inE != nil {
        return DriverResult{false, "internal error: " + inE.String()}
    }

    if outE != nil {
        return DriverResult{false, "internal error: " + outE.String()}
    }

    defer inR.Close()
    defer inW.Close()
    defer outR.Close()
    defer outW.Close()

    zooRoot := "/home/ashley/zoo/compd/"
    argv := []string{"dash", "../drivers/"+driver}
    envv := []string{"ZOO_ROOT="+zooRoot}
    fds := []*os.File{inR, outW, outW}
    prog := zooRoot + "/dash/bin/dash"
    dir := zooRoot + "/scratch/"

    child, err := os.StartProcess(prog, argv, envv, dir, fds)

    if err != nil {
        return DriverResult{false, "internal error: " + err.String()}
    }
    log.Println("driver: "+driver)
    io.WriteString(inW, source)
    inW.Close()

    child.Wait(0)
    outW.Close()
    result, _ := ioutil.ReadAll(outR)
    return DriverResult{true, string(result)}
}

func CompileServer(w http.ResponseWriter, req *http.Request) {
    driver := req.FormValue("driver")
    source := req.FormValue("source")
    ok := true

    if strings.Contains(driver, "/") {
        ok = false
    }

    if ok {
        dr := RunDriver(driver, source)
        bytes, _ := json.Marshal(dr)
        w.Write(bytes)
    } else {
        w.WriteHeader(500)
    }
}

func main() {
    http.HandleFunc("/", CompileServer)
    err := http.ListenAndServe(":7777", nil)
    if err != nil {
        log.Fatal("ListenAndServe: ", err.String())
    }
}
