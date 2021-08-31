
proc OnBegin run {
    set hostname "redacted for github"
    set port "56125"
    set message "Begin $run"
    puts "Sending \"$message\" to $hostname"
    exec echo $message | nc $hostname $port
}

proc OnEnd run {
    set hostname "redacted for github"
    set port "56125"
    set message "End $run"
    puts "Sending \"$message\" to $hostname"
    exec echo $message | nc $hostname $port
}

