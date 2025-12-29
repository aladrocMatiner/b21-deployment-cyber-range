#!/bin/bash
echo "Do you really whish to stop the crl system (including all worlds and events)?"
select yn in "Yes" "No"; do
    case $yn in
        Yes ) docker stack ls|grep ^crl|cut -f1 -d" "|xargs docker stack rm ; break;;
        No ) exit;;
    esac
done

echo "Do you really whish to purge the crl system config (ie removing Events folder)?"
select yn in "Yes" "No"; do
    case $yn in
        Yes ) rm -rf Events ; break;;
        No ) exit;;
    esac
done

